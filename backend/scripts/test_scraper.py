import asyncio
import logging
from app.services.scraper.result_scraper import scrape_lottery_results

logging.basicConfig(level=logging.INFO)

async def main():
    results = await scrape_lottery_results(days_back=7)
    print(f"Total results: {len(results)}")

    found = {r.match_id: r for r in results}
    for mid in ['周日210', '周日211', '周日212', '周日213', '周日214', '周日215', '周日216', '周日217', '周日218']:
        if mid in found:
            r = found[mid]
            print(f"FOUND {mid}: {r.home_team} vs {r.away_team} {r.full_time_score}")
        else:
            print(f"MISSING {mid}")

if __name__ == "__main__":
    asyncio.run(main())
