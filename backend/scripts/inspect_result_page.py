import requests
import re

r = requests.get('https://www.lottery.gov.cn/jc/zqsgkj/', headers={'User-Agent':'Mozilla/5.0'}, timeout=15)
html = r.text
print('status:', r.status_code)

# find script src
scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
print('external scripts:', scripts[:30])

# find getUniformMatchResult references
for m in re.finditer(r'getUniformMatchResult[^"\']*', html):
    print('FOUND in html:', m.group(0)[:200])

# try to fetch main js files and search
for src in scripts:
    if src.startswith('//'):
        url = 'https:' + src
    elif src.startswith('http'):
        url = src
    else:
        url = 'https://www.lottery.gov.cn' + src
    try:
        js = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=10).text
        if 'getUniformMatchResult' in js:
            print('FOUND in', url)
            for m in re.finditer(r'.{0,100}getUniformMatchResult.{0,200}', js):
                print('  ', m.group(0)[:300])
    except Exception as e:
        print('failed to fetch', url, e)
