import asyncio
import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from app.services.scraper.fetcher import fetch_html
from app.services.scraper.parser import ParsedResult

logger = logging.getLogger(__name__)


RESULTS_URL = "https://www.lottery.gov.cn/jc/zqsgkj/"
API_URL_PATTERN = "gateway/uniform/football/getUniformMatchResultV1.qry"


def _build_detail_url(mid: str) -> str:
    return f"https://www.sporttery.cn/jc/zqdz/index.html?showType=2&mid={mid}"


def parse_score_from_html(html: str) -> Optional[Tuple[int, int]]:
    """
    尝试从比赛详情页 HTML 中解析最终比分。
    由于页面结构可能变化，这里使用多种启发式规则。
    """
    if not html:
        return None

    # 常见比分展示形式："2:1"、"2 - 1"、"2：1"
    candidates = []
    patterns = [
        re.compile(r"比分\s*[:：]\s*(\d+)\s*[:：-]\s*(\d+)"),
        re.compile(r"full.?.?time.*?score\D*(\d+)[\s:-]+(\d+)", re.IGNORECASE),
        re.compile(r"(\d+)\s*[:：-]\s*(\d+)\s*<[^>]*>\s*(?:完|全场|FT|Full Time)"),
    ]
    for pat in patterns:
        for m in pat.finditer(html):
            try:
                candidates.append((int(m.group(1)), int(m.group(2))))
            except ValueError:
                pass

    # 从 script/json 中尝试找比分字段
    json_patterns = [
        re.compile(r'"homeScore"\s*:\s*(\d+).*?"awayScore"\s*:\s*(\d+)', re.S),
        re.compile(r'"hscore"\s*:\s*"?(\d+)"?.*?"ascore"\s*:\s*"?(\d+)"?', re.S),
        re.compile(r'"score"\s*:\s*"(\d+)[\s:-](\d+)"', re.S),
    ]
    for pat in json_patterns:
        m = pat.search(html)
        if m:
            try:
                candidates.append((int(m.group(1)), int(m.group(2))))
            except ValueError:
                pass

    if not candidates:
        return None

    # 取出现次数最多的候选
    from collections import Counter
    most_common = Counter(candidates).most_common(1)[0][0]
    return most_common


def fetch_match_result(mid: str) -> Optional[Tuple[int, int]]:
    """根据 mid 抓取比赛实际比分（单个比赛详情页兜底）。"""
    url = _build_detail_url(mid)
    html = fetch_html(url)
    if not html:
        return None
    return parse_score_from_html(html)


def _match_result_from_score(score_str: Optional[str]) -> Optional[str]:
    """把 '2:0' 这种比分转换为主队视角的赛果：胜/平/负。"""
    if not score_str:
        return None
    m = re.match(r"(\d+):(\d+)", score_str)
    if not m:
        return None
    home, away = int(m.group(1)), int(m.group(2))
    if home > away:
        return "胜"
    if home == away:
        return "平"
    return "负"


def half_full_result(half_score: Optional[str], full_score: Optional[str]) -> Optional[str]:
    """根据半场和全场比分生成半全场结果，如 胜/胜。"""
    half = _match_result_from_score(half_score)
    full = _match_result_from_score(full_score)
    if half and full:
        return f"{half}/{full}"
    return None


def _normalize_score(score: Optional[str]) -> Optional[str]:
    """统一比分格式为 'H:A'。"""
    if not score:
        return None
    score = score.strip()
    if score in ("", "--", "取消", "无效"):
        return None
    m = re.match(r"(\d+)\s*[:：\-]\s*(\d+)", score)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    return None


def _parse_api_results(data: dict) -> List[ParsedResult]:
    """解析体彩赛果 API 返回的 JSON。"""
    results: List[ParsedResult] = []
    value = data.get("value") or {}
    matches = value.get("matchResult") or []

    for item in matches:
        full_score = _normalize_score(item.get("sectionsNo999"))
        if not full_score:
            # 全场比分缺失则跳过（未结束或无效场次）
            continue

        half_score = _normalize_score(item.get("sectionsNo1"))
        match_date_str = item.get("matchDate")
        try:
            match_date = datetime.strptime(match_date_str, "%Y-%m-%d").date() if match_date_str else date.today()
        except ValueError:
            match_date = date.today()

        results.append(
            ParsedResult(
                match_id=item.get("matchNumStr", ""),
                mid=str(item.get("matchId")) if item.get("matchId") else None,
                match_date=match_date,
                league=item.get("leagueNameAbbr", ""),
                home_team=item.get("homeTeam", ""),
                away_team=item.get("awayTeam", ""),
                half_time_score=half_score,
                full_time_score=full_score,
                status=str(item.get("poolStatus", "")),
            )
        )

    logger.info("Parsed %d match results from API", len(results))
    return results


async def scrape_lottery_results(
    days_back: int = 7,
    headless: bool = True,
) -> List[ParsedResult]:
    """从体彩赛果开奖页批量抓取已结束比赛结果。

    通过 Playwright 渲染页面、设置日期范围并点击查询，
    监听赛果 API 响应以获取 JSON 数据。
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        logger.error("Playwright not installed: %s", exc)
        return []

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    captured_responses = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        page = await context.new_page()

        def handle_response(response):
            if API_URL_PATTERN in response.url:
                captured_responses.append(response)

        page.on("response", handle_response)

        try:
            await page.goto(RESULTS_URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_selector("#start_date", timeout=30000)

            await page.fill("#start_date", start_date)
            await page.fill("#end_date", end_date)
            await page.click("a.u-btn:has-text('开始查询')")

            # 等待 API 响应
            for _ in range(30):
                await asyncio.sleep(0.5)
                if captured_responses:
                    break

            if not captured_responses:
                logger.warning("No results API response captured")
                await browser.close()
                return []

            response = captured_responses[-1]
            body = await response.body()
            data = json.loads(body)
            await browser.close()
            return _parse_api_results(data)
        except Exception as exc:
            logger.error("Failed to scrape results: %s", exc)
            await browser.close()
            return []
