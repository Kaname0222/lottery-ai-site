import logging
from datetime import date
from typing import List, Dict
from app.services.scraper.fetcher import (
    fetch_html_with_playwright,
    fetch_score_odds_html,
    fetch_score_odds_via_api,
)
from app.services.scraper.parser import (
    parse_lottery_matches,
    parse_score_odds,
    parse_score_odds_from_api,
    parse_total_goals_odds,
    parse_half_full_odds,
    ParsedMatch,
)

logger = logging.getLogger(__name__)

SCHEDULE_URLS = {
    "spf": "https://www.lottery.gov.cn/jc/jsq/zqspf/",
    "bf": "https://www.lottery.gov.cn/jc/jsq/zqbf/",
    "zjq": "https://www.lottery.gov.cn/jc/jsq/zqzjq/",
    "bqc": "https://www.lottery.gov.cn/jc/jsq/zqbqc/",
}


async def _fetch_html(url: str) -> str:
    html = await fetch_html_with_playwright(url)
    if not html:
        logger.error("Failed to retrieve %s", url)
        return ""
    return html


async def scrape_matches() -> List[ParsedMatch]:
    """抓取中国体彩竞彩足球当前在售赛程及全部玩法赔率。"""
    spf_html = await _fetch_html(SCHEDULE_URLS["spf"])
    if not spf_html:
        return []

    matches = parse_lottery_matches(spf_html)
    if not matches:
        logger.warning("No matches found on SPF page")
        return []

    match_map: Dict[str, ParsedMatch] = {m.match_id: m for m in matches}

    # 抓取并合并其它玩法赔率
    # 比分赔率优先走统一接口，失败再回退到 Playwright 渲染页面
    score_odds_data = fetch_score_odds_via_api()
    if score_odds_data:
        score_odds = parse_score_odds_from_api(score_odds_data)
        logger.info("Using score odds from API")
    else:
        bf_html = await fetch_score_odds_html(SCHEDULE_URLS["bf"], wait_ms=4000)
        score_odds = parse_score_odds(bf_html)
        logger.info("Using score odds from HTML fallback")
    for match_id, odds in score_odds.items():
        if match_id in match_map:
            match_map[match_id].score_odds = odds

    zjq_html = await _fetch_html(SCHEDULE_URLS["zjq"])
    for match_id, odds in parse_total_goals_odds(zjq_html).items():
        if match_id in match_map:
            match_map[match_id].total_goals_odds = odds

    bqc_html = await _fetch_html(SCHEDULE_URLS["bqc"])
    for match_id, odds in parse_half_full_odds(bqc_html).items():
        if match_id in match_map:
            match_map[match_id].half_full_odds = odds

    logger.info("Scraped %d matches with full odds", len(matches))
    return matches


async def scrape_matches_for_date(target_date: date) -> List[ParsedMatch]:
    """抓取并过滤指定日期的比赛。"""
    all_matches = await scrape_matches()
    return [m for m in all_matches if m.match_date == target_date]
