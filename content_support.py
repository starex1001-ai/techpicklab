"""Shared content contract for the five supplied repositories. Python 3.10+."""
import re
from datetime import date, datetime, timezone, timedelta
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit

KST = timezone(timedelta(hours=9))

def today():
    return datetime.now(KST).date()

class BodyInspector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag in {'script','iframe','object','embed','form','input','button','style','link','meta','base','html','head','body','title'}:
            raise ValueError('蹂몃ЦHTML?먮뒗 蹂몃Ц ?쒓렇留??ъ슜?섏꽭?? '+tag)
        for name, value in attrs:
            if name.lower().startswith('on') or name in {'srcdoc'}:
                raise ValueError('蹂몃ЦHTML???ㅽ뻾 ?띿꽦? ?덉슜?섏? ?딆뒿?덈떎: '+name)
            if name in {'href','src','action','poster','xlink:href'} and value:
                compact = re.sub(r'[\s\x00-\x20]+','',value)
                if urlsplit(compact).scheme.lower() not in {'','https','http','mailto','tel'}:
                    raise ValueError('吏?먰븯吏 ?딅뒗 蹂몃Ц 留곹겕 ?뺤떇')
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
    def handle_data(self, data):
        self.text.append(data)

def plain_text(body):
    parser = BodyInspector()
    parser.feed(body)
    parser.close()
    return re.sub(r'\s+',' ',' '.join(parser.text)).strip()

def render_body(post):
    body = post['body_html']
    plain_text(body)
    toc = []
    used = set(re.findall(r'\bid=["\']([^"\']+)', body))
    def heading(match):
        attrs, text = match.group(1), match.group(2)
        found = re.search(r'\bid=["\']([^"\']+)["\']',attrs)
        ident = found.group(1) if found else 'auto-section-'+str(len(toc)+1)
        if not found:
            while ident in used:
                ident += '-new'
            used.add(ident)
            attrs += ' id="'+ident+'"'
        toc.append('<li><a href="#'+escape(ident,quote=True)+'">'+escape(plain_text(text))+'</a></li>')
        return '<h2'+attrs+'>'+text+'</h2>'
    body = re.sub(r'<h2\b([^>]*)>(.*?)</h2>',heading,body,flags=re.I|re.S)
    tags = post.get('tags',[])
    if tags:
        body += '<p class="post-tags" aria-label="?쒓렇">'+' 쨌 '.join('#'+escape(t) for t in tags)+'</p>'
    return ''.join(toc), body

def validate_posts(posts, config, public=None):
    if not isinstance(posts,list):
        raise ValueError('content/posts.json must be an array')
    categories = {c['slug'] for c in config['categories']}
    slugs, ids = set(), set()
    for p in posts:
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',p['slug']):
            raise ValueError('Invalid slug: '+p['slug'])
        if p['slug'] in slugs or p['id'] in ids:
            raise ValueError('Duplicate slug or id')
        slugs.add(p['slug']); ids.add(p['id'])
        if public and not p.get('legacy', False) and (public/'posts'/p['slug']).exists():
            raise ValueError('湲곗〈 HTML 湲??URL怨?異⑸룎?⑸땲?? '+p['slug'])
        if p['category'] not in categories or p['status'] not in {'draft','published'}:
            raise ValueError('Invalid category or status')
        if not p.get('legacy', False) and date.fromisoformat(p['updated']) < date.fromisoformat(p['date']):
            raise ValueError('Update date precedes publication')
        for field in ['id','title','description','label','intro']:
            if not isinstance(p[field],str):
                raise ValueError('Expected string: '+field)
        if not isinstance(p['minutes'],int) or p['minutes'] < 1:
            raise ValueError('Invalid reading time')
        if 'body_html' in p:
            if not isinstance(p['body_html'],str) or not plain_text(p['body_html']):
                raise ValueError('Empty body')
        if not isinstance(p.get('tags',[]),list) or any(not isinstance(t,str) for t in p.get('tags',[])):
            raise ValueError('Invalid tags')


