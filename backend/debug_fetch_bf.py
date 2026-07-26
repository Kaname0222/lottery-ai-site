import asyncio
from app.services.scraper.fetcher import fetch_score_odds_html
from app.services.scraper.parser import parse_score_odds

async def main():
    url = "https://www.lottery.gov.cn/jc/jsq/zqbf/"
    html = await fetch_score_odds_html(url, wait_ms=5000)
    if html:
        odds = parse_score_odds(html)
        print(f"Fetched score odds for {len(odds)} matches")
        for match_id in sorted(odds.keys()):
            print(f"  {match_id}: {len(odds[match_id])} odds")
    else:
        print("Failed to fetch")

asyncio.run(main())
