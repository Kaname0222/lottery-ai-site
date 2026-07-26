import re
from app.services.scraper.fetcher import fetch_html

mid = '2040632'
url = f'https://www.sporttery.cn/jc/zqdz/index.html?showType=2&mid={mid}'
html = fetch_html(url)

print('Gateway URLs:')
for m in re.finditer(r'https?://[^\s"\'<>]*gateway[^\s"\'<>]*', html):
    print(m.group(0))

print('\nAPI URLs in JS files:')
for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', html):
    src = m.group(1)
    if src.endswith('.js'):
        if src.startswith('//'):
            js_url = 'https:' + src
        elif src.startswith('http'):
            js_url = src
        else:
            js_url = 'https://www.sporttery.cn' + src
        try:
            js_html = fetch_html(js_url)
            if js_html and ('gateway' in js_html.lower() or 'api' in js_html.lower()):
                print(f'\n{js_url}:')
                for mm in re.finditer(r'https?://[^\s"\'<>]*gateway[^\s"\'<>]*', js_html):
                    print('  ', mm.group(0))
        except Exception as e:
            print(f'Failed to fetch {js_url}: {e}')
