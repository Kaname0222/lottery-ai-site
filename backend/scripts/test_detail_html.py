from app.services.scraper.fetcher import fetch_html
import re

mid = '2040632'
url = f'https://www.sporttery.cn/jc/zqdz/index.html?showType=2&mid={mid}'
html = fetch_html(url)

# Find API URLs
for m in re.finditer(r'https?://[^\s"\'<>]+', html):
    url = m.group(0)
    if 'api' in url.lower() or 'gateway' in url.lower() or 'sporttery' in url.lower():
        print(url)

# Find JS files
print('\n--- JS files ---')
for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', html):
    print(m.group(1))

# Find fetch/axios calls
for m in re.finditer(r'\$\.get|axios\.get|fetch\(|getMatch|matchInfo|FBonus', html):
    idx = m.start()
    print('---', m.group(0), '---')
    print(html[max(0, idx-100):idx+300])
