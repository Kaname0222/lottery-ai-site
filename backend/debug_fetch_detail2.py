import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def main():
    mid = "2040613"
    url = f"https://www.sporttery.cn/jc/zqdz/index.html?showType=2&mid={mid}"
    print(f"Fetching {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)
        html = await page.content()
        await browser.close()
    
    soup = BeautifulSoup(html, 'lxml')
    print(f"Title: {soup.title.get_text() if soup.title else 'No title'}")
    print(f"Body length: {len(soup.body.get_text()) if soup.body else 0}")
    
    # 打印页面文本前 2000 字符
    text = soup.get_text(separator='\n')
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    print("\n".join(lines[:80]))

asyncio.run(main())
