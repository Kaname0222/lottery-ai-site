import re
from app.services.scraper.fetcher import fetch_html

url = 'https://static.sporttery.cn/res_1_0/jcw/default/jc/zqdz.js'
js = fetch_html(url)

# Find getFixedBonus context
idx = js.find('getFixedBonus')
if idx != -1:
    print(js[max(0, idx-500):idx+1500])

# Also find getMatchHead
idx = js.find('getMatchHead')
if idx != -1:
    print('\n--- getMatchHead ---')
    print(js[max(0, idx-200):idx+500])
