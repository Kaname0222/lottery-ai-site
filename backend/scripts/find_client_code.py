import re
from app.services.scraper.fetcher import fetch_html

url = 'https://static.sporttery.cn/res_1_0/common/js/commonV1.js'
js = fetch_html(url)
print(f'JS length: {len(js) if js else 0}')
if not js:
    exit()

for keyword in ['comClientCode', 'clientCode']:
    for m in re.finditer(keyword, js):
        idx = m.start()
        context = js[max(0, idx-200):idx+300]
        print(f'--- {keyword} ---')
        print(context)
        print()
