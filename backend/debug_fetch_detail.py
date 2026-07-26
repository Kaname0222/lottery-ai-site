import asyncio
from app.services.scraper.fetcher import fetch_html_with_playwright
from bs4 import BeautifulSoup

async def main():
    # 周六202 的 mid
    mid = "2040613"
    url = f"https://www.sporttery.cn/jc/zqdz/index.html?showType=2&mid={mid}"
    print(f"Fetching {url}")
    html = await fetch_html_with_playwright(url, wait_ms=5000)
    if not html:
        print("Failed")
        return
    
    soup = BeautifulSoup(html, 'lxml')
    print(f"Title: {soup.title.get_text() if soup.title else 'No title'}")
    
    # 查找比分赔率相关元素
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables")
    
    # 查找包含 "1:0" 的元素
    for elem in soup.find_all(text=lambda t: t and '1:0' in t):
        parent = elem.parent
        print(f"Found 1:0 in {parent.name}: {elem.strip()[:100]}")
        break

asyncio.run(main())
