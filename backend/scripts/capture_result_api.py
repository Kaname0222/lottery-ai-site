import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        urls = []

        def handle_response(response):
            if "getUniformMatchResult" in response.url:
                urls.append(response.url)
                print("CAPTURED:", response.url)

        page.on("response", handle_response)
        await page.goto("https://www.lottery.gov.cn/jc/zqsgkj/", wait_until="networkidle", timeout=60000)
        await page.wait_for_selector("#start_date", timeout=30000)
        await page.fill("#start_date", "2026-07-20")
        await page.fill("#end_date", "2026-07-27")
        await page.click("a.u-btn:has-text('开始查询')")
        for _ in range(30):
            await asyncio.sleep(0.5)
            if urls:
                break
        await browser.close()
        print("DONE, captured:", urls)


if __name__ == "__main__":
    asyncio.run(main())
