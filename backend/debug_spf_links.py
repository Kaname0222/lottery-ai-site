import asyncio
from app.services.scraper.fetcher import fetch_html_with_playwright
from bs4 import BeautifulSoup

async def main():
    url = "https://www.lottery.gov.cn/jc/jsq/zqspf/"
    html = await fetch_html_with_playwright(url, wait_ms=3000)
    if not html:
        print("Failed")
        return
    soup = BeautifulSoup(html, 'lxml')
    links = soup.find_all('a', href=True)
    for link in links:
        href = link['href']
        if 'mid=' in href:
            print(f"{link.get_text(strip=True)[:30]} -> {href}")

asyncio.run(main())
