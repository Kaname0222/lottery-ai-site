import asyncio
from app.services.scraper.china_sports_lottery import scrape_matches

async def main():
    matches = await scrape_matches()
    print(f"Scraped {len(matches)} matches")
    for m in matches[:5]:
        has_score = '有' if m.score_odds else '无'
        print(f"  {m.match_id}: {m.home_team} VS {m.away_team} | score_odds={has_score}")
    # 检查周日202
    target = next((m for m in matches if m.match_id == '周日202'), None)
    if target:
        print(f"\n周日202 score_odds sample: {list(target.score_odds.items())[:5] if target.score_odds else None}")

asyncio.run(main())
