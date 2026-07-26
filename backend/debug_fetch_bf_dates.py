import asyncio
from app.services.scraper.fetcher import fetch_html_with_playwright
from bs4 import BeautifulSoup

URLS = [
    "https://www.lottery.gov.cn/jc/jsq/zqbf/",
    "https://www.lottery.gov.cn/jc/jsq/zqbf/?d=2026-07-26",
    "https://www.lottery.gov.cn/jc/jsq/zqbf/?date=2026-07-26",
    "https://www.lottery.gov.cn/jc/jsq/zqbf/?matchDate=2026-07-26",
    "https://www.lottery.gov.cn/jc/jsq/zqbf/?saleDate=2026-07-26",
]

async def main():
    for url in URLS:
        print(f"\nTrying: {url}")
        html = await fetch_html_with_playwright(url, wait_ms=3000)
        if not html:
            print("  Failed")
            continue
        soup = BeautifulSoup(html, 'lxml')
        table = soup.find('table', id='mainTbl')
        if not table:
            print("  No mainTbl")
            continue
        rows = table.find_all('tr', class_='listTr')
        match_ids = []
        for row in rows:
            tds = row.find_all('td')
            if tds:
                text = ' '.join(tds[0].get_text().split())
                match_ids.append(text)
        print(f"  Found {len(match_ids)} matches: {', '.join(match_ids[:10])}")

asyncio.run(main())
