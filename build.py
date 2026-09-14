"""Tech Pick Lab generator. Existing pages are copied byte-for-byte."""
import argparse
import json
import re
import shutil
from pathlib import Path
from datetime import date
from html import escape as e
from content_support import render_body, today

def build(root):
    root = Path(root).resolve()
    config = json.loads((root / 'site.json').read_text(encoding='utf-8'))
    posts = json.loads((root / 'content/posts.json').read_text(encoding='utf-8'))
    base = config['url'].rstrip('/')
    categories = {c['slug']: c['name'] for c in config['categories']}
    seen, ids = set(), set()
    additions = []
    for post in posts:
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', post['slug']):
            raise ValueError('Invalid slug')
        if post['slug'] in seen or post['id'] in ids:
            raise ValueError('Duplicate slug or id')
        seen.add(post['slug']); ids.add(post['id'])
        if post['category'] not in categories or post['status'] not in ('draft', 'published'):
            raise ValueError('Invalid category or status')
        if post.get('legacy'):
            if not (root / 'public/posts' / post['slug'] / 'index.html').is_file():
                raise ValueError('Missing preserved post')
            continue
        date.fromisoformat(post['date']); date.fromisoformat(post['updated'])
        if post['updated'] < post['date']:
            raise ValueError('Invalid update date')
        render_body(post)
        if (root / 'public/posts' / post['slug']).exists():
            raise ValueError('Cannot replace preserved post')
        if post['status'] == 'published' and post['date'] <= today().isoformat():
            additions.append(post)
    additions.sort(key=lambda p: (p['date'], p['id']), reverse=True)
    out = root / 'dist'
    if out.is_symlink() or out.resolve().parent != root:
        raise ValueError('Unsafe output path')
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(root / 'public', out)
    sample = (root / 'templates/post.html').read_text(encoding='utf-8')
    def write(path, text):
        dest = out / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding='utf-8')
    for p in additions:
        url = base + '/posts/' + p['slug'] + '/'
        head = sample.split('</head>')[0]
        head = re.sub(r'<title>.*?</title>', lambda m: '<title>' + e(p['title']) + ' | ' + e(config['name']) + '</title>', head)
        for attr, key, value in [('name', 'description', p['description']), ('property', 'og:title', p['title']), ('property', 'og:description', p['description']), ('property', 'og:url', url)]:
            head = re.sub(r'<meta ' + attr + '="' + key + r'" content="[^"]*">', lambda m: '<meta ' + attr + '="' + key + '" content="' + e(value, quote=True) + '">', head)
        head = re.sub(r'<link rel="canonical" href="[^"]*">', lambda m: '<link rel="canonical" href="' + e(url, quote=True) + '">', head)
        schema = {'@context': 'https://schema.org', '@type': 'BlogPosting', 'headline': p['title'], 'description': p['description'], 'inLanguage': 'ko-KR', 'mainEntityOfPage': url, 'datePublished': p['date'], 'dateModified': p['updated'], 'author': {'@type': 'Organization', 'name': config['name'], 'url': base + '/about/'}, 'publisher': {'@type': 'Organization', 'name': config['name'], 'url': base}}
        if p.get('image_url'):
            schema['image'] = p['image_url'] if p['image_url'].startswith('https://') else base + p['image_url']
            head += '<meta property="og:image" content="' + e(schema['image'], quote=True) + '">'
        data = json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c')
        head = re.sub(r'<script type="application/ld\+json">.*?</script>', lambda m: '<script type="application/ld+json">' + data + '</script>', head)
        before = sample.split('</head>')[1].split('<article class="prose">')[0]
        after = sample.split('</article>', 1)[1]
        toc, body = render_body(p)
        category = e(categories[p['category']])
        article = '<article class="prose"><div class="crumb"><a href="/">홈</a> / <a href="/category/' + p['category'] + '/">' + category + '</a></div><p class="eyebrow">' + category + '</p><h1>' + e(p['title']) + '</h1><p class="lead">' + e(p['description']) + '</p><p class="byline">글 · ' + e(config['name']) + ' | <time datetime="' + p['date'] + '">' + p['date'] + '</time></p>'
        if toc:
            article += '<nav class="toc" aria-label="글 목차"><strong>이 글에서 살펴볼 내용</strong><ol>' + toc + '</ol></nav>'
        article += body + '<h2>다음으로 읽기</h2>'
        for q in posts[:3]:
            if q['id'] != p['id'] and q.get('legacy'):
                article += '<p><a href="/posts/' + q['slug'] + '/">' + e(q['title']) + ' ↗</a></p>'
        write('posts/' + p['slug'] + '/index.html', head + '</head>' + before + article + '</article>' + after)
    def card(p):
        link = '/posts/' + p['slug'] + '/'
        return '<article class="card"><span class="eyebrow">' + e(categories[p['category']]) + '</span><h3><a href="' + link + '">' + e(p['title']) + '</a></h3><p>' + e(p['description']) + '</p><a class="read" href="' + link + '">가이드 읽기 <span aria-hidden="true">↗</span></a></article>'
    if additions:
        home = (out / 'index.html').read_text(encoding='utf-8')
        home = home.replace('<div class="grid">', '<div class="grid">' + ''.join(card(p) for p in additions[:12]), 1)
        home = home.replace('GUIDES / 01—03', 'GUIDES / ' + str(len(posts)))
        write('index.html', home)
        for category in categories:
            selected = [p for p in additions if p['category'] == category]
            if selected:
                path = 'category/' + category + '/index.html'
                page = (out / path).read_text(encoding='utf-8')
                write(path, page.replace('<div class="grid listing">', '<div class="grid listing">' + ''.join(card(p) for p in selected), 1))
        sitemap = (out / 'sitemap.xml').read_text(encoding='utf-8')
        extra = ''.join('<url><loc>' + e(base + '/posts/' + p['slug'] + '/') + '</loc><lastmod>' + p['updated'] + '</lastmod></url>\n' for p in additions)
        write('sitemap.xml', sitemap.replace('</urlset>', extra + '</urlset>'))
    print('Built Tech Pick Lab:', len(additions), 'new posts; original pages preserved')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', default=str(Path(__file__).parent))
    build(parser.parse_args().site)
