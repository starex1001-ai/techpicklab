"""Shared, strict HTML renderer for new automated posts (stdlib only)."""
import re
from datetime import datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

KST = timezone(timedelta(hours=9))

def today():
    return datetime.now(KST).date()

def safe_url(value, image=False):
    if any(ord(c) < 32 for c in value) or '\\' in value:
        raise ValueError('Invalid URL characters')
    u = urlsplit(value)
    if value.startswith('/') and not value.startswith('//'):
        if '..' in u.path.split('/'):
            raise ValueError('Parent paths are not allowed')
        return value
    if not image and value.startswith('#'):
        return value
    if u.scheme == 'https' and u.hostname and not u.username and not u.password:
        return value
    if not image and u.scheme == 'mailto' and u.path:
        return value
    raise ValueError('Use an HTTPS URL or a site-relative path')

class BodyParser(HTMLParser):
    tags = set('p div span section h2 h3 h4 h5 h6 ul ol li a img figure figcaption blockquote pre code strong em b i u s del br hr table thead tbody tfoot tr th td caption details summary sup sub'.split())
    void = {'img', 'br', 'hr'}
    attrs = {'id', 'class', 'title', 'lang', 'dir', 'style', 'align'}
    per_tag = {'a': {'href', 'target', 'rel'}, 'img': {'src', 'alt', 'width', 'height', 'loading'}, 'ol': {'start'}, 'td': {'colspan', 'rowspan'}, 'th': {'colspan', 'rowspan', 'scope'}}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.stack, self.toc, self.ids = [], [], [], set()
        self.heading = None

    def handle_starttag(self, tag, attrs):
        if tag not in self.tags:
            raise ValueError('Unsupported body HTML tag: ' + tag)
        values = dict(attrs)
        if len(values) != len(attrs):
            raise ValueError('Duplicate HTML attribute')
        for key, value in attrs:
            if key not in self.attrs | self.per_tag.get(tag, set()) or value is None:
                raise ValueError('Unsupported HTML attribute: ' + key)
            if key in ('href', 'src'):
                safe_url(value, key == 'src')
            if key == 'style':
                # Keep simple editor formatting, reject active CSS and resource loads.
                if not re.fullmatch(r'[a-zA-Z0-9\s:;#.,%()\-]+', value) or re.search(r'url|expression|import|behavior|binding', value, re.I):
                    raise ValueError('Unsupported inline style')
            if key in ('width', 'height', 'colspan', 'rowspan', 'start') and not re.fullmatch(r'[1-9][0-9]{0,4}', value):
                raise ValueError('Invalid numeric HTML attribute')
        if tag == 'img':
            if not values.get('src') or not values.get('alt', '').strip():
                raise ValueError('Every image needs src and descriptive alt text')
            values.setdefault('loading', 'lazy')
        if tag == 'a' and values.get('target') == '_blank':
            values['rel'] = 'noopener noreferrer'
        if tag == 'h2':
            values.setdefault('id', 'auto-section-' + str(len(self.toc)))
            self.heading = [values['id'], '']
        if 'id' in values:
            if values['id'] in self.ids:
                raise ValueError('Duplicate HTML id')
            self.ids.add(values['id'])
        self.parts.append('<' + tag + ''.join(' ' + k + '="' + escape(v, quote=True) + '"' for k, v in values.items()) + '>')
        if tag not in self.void:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            raise ValueError('Unbalanced body HTML: ' + tag)
        self.stack.pop()
        self.parts.append('</' + tag + '>')
        if tag == 'h2':
            self.toc.append(tuple(self.heading))
            self.heading = None

    def handle_data(self, data):
        self.parts.append(escape(data))
        if self.heading is not None:
            self.heading[1] += data

    def handle_decl(self, decl):
        raise ValueError('Body must be an HTML fragment')

def render_body(post):
    parser = BodyParser()
    parser.feed(post['body_html'])
    parser.close()
    if parser.stack:
        raise ValueError('Unclosed body HTML tag: ' + parser.stack[-1])
    body = ''.join(parser.parts)
    if not re.sub('<[^>]+>', '', body).strip():
        raise ValueError('Body text is empty')
    toc = ''.join('<li><a href="#' + escape(key, quote=True) + '">' + escape(title) + '</a></li>' for key, title in parser.toc)
    if post.get('image_url'):
        safe_url(post['image_url'], True)
        if not post.get('image_alt', '').strip():
            raise ValueError('image_alt is required with image_url')
        body = '<figure><img src="' + escape(post['image_url'], quote=True) + '" alt="' + escape(post['image_alt'], quote=True) + '" loading="lazy"></figure>' + body
    style = '<style>.auto-content img{max-width:100%;height:auto}.auto-content figure{margin:1.5em 0}.auto-content table{display:block;max-width:100%;overflow:auto}.auto-content pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
    marker = ''
    if post.get('source_hash'):
        if not re.fullmatch(r'[a-f0-9]{64}', post['source_hash']):
            raise ValueError('Invalid source hash')
        marker = '<span hidden data-auto-publish="' + post['source_hash'] + '"></span>'
    return toc, marker + style + '<div class="auto-content">' + body + '</div>'
