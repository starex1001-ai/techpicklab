"""Preserve original static pages; add content/posts.json articles to dist/."""
import argparse
import json
import re
import shutil
from pathlib import Path
from html import escape as e
from xml.etree import ElementTree as ET
from content_support import render_body, validate_posts, today

def build(root):
    root = Path(root).resolve()
    public, out = root/'public', root/'dist'
    config = json.loads((root/'site.json').read_text(encoding='utf-8'))
    posts = json.loads((root/'content/posts.json').read_text(encoding='utf-8'))
    base = config['url'].rstrip('/')
    if not re.fullmatch(r'https://[a-z0-9.-]+',base):
        raise ValueError('Invalid site URL')
    # Retained pages contain canonical URLs. Never silently mix domains.
    home = (public/'index.html').read_text(encoding='utf-8')
    if f'rel="canonical" href="{base}/"' not in home:
        raise ValueError('site.json URL differs from the preserved HTML canonical domain')
    validate_posts(posts,config,public)
    posts = sorted([p for p in posts if p['status']=='published' and p['date']<=today().isoformat()],key=lambda p:(p['date'],p['id']),reverse=True)
    if out.is_symlink():
        raise ValueError('dist must not be a symlink')
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(public,out)
    if not posts:
        print('Built original site unchanged (no new posts)')
        return
    categories = {c['slug']:c['name'] for c in config['categories']}
    template = (public/'posts/device-checklist/index.html').read_text(encoding='utf-8')
    def write(path,text):
        dest = out/path
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(text,encoding='utf-8')
    def card(p):
        route = '/posts/'+p['slug']+'/'
        return f'<article class="card"><span class="eyebrow">{e(categories[p["category"]])}</span><h3><a href="{route}">{e(p["title"])}</a></h3><p>{e(p["description"])}</p><a class="read" href="{route}">가이드 읽기 <span aria-hidden="true">↗</span></a></article>'
    for p in posts:
        url = base+'/posts/'+p['slug']+'/'
        toc, body = render_body(p)
        schema = {'@context':'https://schema.org','@type':'BlogPosting','headline':p['title'],'description':p['description'],'inLanguage':'ko-KR','mainEntityOfPage':url,'datePublished':p['date'],'dateModified':p['updated'],'keywords':p.get('tags',[]),'author':{'@type':'Organization','name':config['name'],'url':base+'/about/'},'publisher':{'@type':'Organization','name':config['name'],'url':base}}
        head = f'<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(p["title"])} | {e(config["name"])}</title><meta name="description" content="{e(p["description"],quote=True)}"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="{url}"><meta property="og:type" content="article"><meta property="og:locale" content="ko_KR"><meta property="og:site_name" content="{e(config["name"])}"><meta property="og:title" content="{e(p["title"],quote=True)}"><meta property="og:description" content="{e(p["description"],quote=True)}"><meta property="og:url" content="{url}"><meta name="theme-color" content="#14283c"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/style.css"><script type="application/ld+json">'+json.dumps(schema,ensure_ascii=False).replace('<','\\u003c')+'</script></head>'
        toc_html = '<nav class="toc" aria-label="글 목차"><strong>이 글에서 살펴볼 내용</strong><ol>'+toc+'</ol></nav>' if toc else ''
        main = f'<main id="main"><article class="prose"><div class="crumb"><a href="/">홈</a> / <a href="/category/{p["category"]}/">{e(categories[p["category"]])}</a></div><p class="eyebrow">{e(categories[p["category"]])}</p><h1>{e(p["title"])}</h1><p class="lead">{e(p["description"])}</p><p class="byline">글 · {e(config["name"])} | <time datetime="{p["date"]}">{p["date"]}</time> · {p["minutes"]}분 읽기</p>{toc_html}{body}</article></main>'
        page = re.sub(r'<head>.*?</head>',lambda _:head,template,count=1,flags=re.S)
        page = re.sub(r'<main\b.*?</main>',lambda _:main,page,count=1,flags=re.S)
        write('posts/'+p['slug']+'/index.html',page)
    # Insert only new cards; leave original cards, head, header and footer intact.
    home = home.replace('<div class="grid">','<div class="grid">'+''.join(card(p) for p in posts),1)
    home = home.replace('GUIDES / 01—03',f'GUIDES / 01—{len(posts)+3:02d}',1)
    write('index.html',home)
    for category in categories:
        selected = [p for p in posts if p['category']==category]
        if selected:
            path = f'category/{category}/index.html'
            source = (public/path).read_text(encoding='utf-8')
            marker = '<div class="grid listing">'
            if source.count(marker)!=1:
                raise ValueError('Unknown category template: '+category)
            write(path,source.replace(marker,marker+''.join(card(p) for p in selected),1))
    ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('',ns)
    tree = ET.parse(public/'sitemap.xml')
    for p in posts:
        entry = ET.SubElement(tree.getroot(),'{'+ns+'}url')
        ET.SubElement(entry,'{'+ns+'}loc').text = base+'/posts/'+p['slug']+'/'
        ET.SubElement(entry,'{'+ns+'}lastmod').text = p['updated']
    tree.write(out/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    print(f'Built preserved site + {len(posts)} new posts: {out}')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--site',default=str(Path(__file__).parent))
    build(parser.parse_args().site)
