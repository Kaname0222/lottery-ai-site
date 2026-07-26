import asyncio
from app.services.scraper.fetcher import fetch_html_with_playwright
from bs4 import BeautifulSoup

async def main():
    url = 'https://www.lottery.gov.cn/jc/zqsgkj/'
    html = await fetch_html_with_playwright(url, wait_ms=8000, wait_selector=None)
    if not html:
        print('Failed')
        return
    soup = BeautifulSoup(html, 'lxml')
    print('Title:', soup.title.get_text() if soup.title else 'No title')
    tables = soup.find_all('table')
    print(f'Tables found: {len(tables)}')
    for i, t in enumerate(tables):
        print(f'  Table {i}: {len(t.find_all("tr"))} rows')
        for r in t.find_all('tr')[:3]:
            print('    ', r.get_text(strip=True)[:100])

asyncio.run(main())
