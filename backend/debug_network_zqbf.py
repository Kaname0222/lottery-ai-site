import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    url = "https://www.lottery.gov.cn/jc/jsq/zqbf/"
    print(f"Fetching {url} and logging network requests")
    
    requests_log = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()
        
        def handle_request(request):
            requests_log.append({
                "url": request.url,
                "method": request.method,
                "resource_type": request.resource_type,
            })
        
        page.on("request", handle_request)
        
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)
        
        # 点击第一个展开按钮，看是否有新的请求
        buttons = await page.query_selector_all("span.folderTd")
        if buttons:
            try:
                await buttons[0].click()
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Click failed: {e}")
        
        await browser.close()
    
    # 输出所有非静态资源请求
    interesting = [r for r in requests_log if r["resource_type"] in ("xhr", "fetch", "document")]
    print(f"\nInteresting requests: {len(interesting)}")
    for r in interesting:
        print(f"  {r['method']} {r['resource_type']}: {r['url']}")
    
    # 保存完整日志
    with open("debug_network_zqbf.json", "w", encoding="utf-8") as f:
        json.dump(requests_log, f, ensure_ascii=False, indent=2)
    print("\nFull log saved to debug_network_zqbf.json")

asyncio.run(main())
