import re
import logging
from datetime import datetime, date
from typing import Dict, List, Optional
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ParsedMatch(BaseModel):
    match_id: str
    mid: Optional[str] = None
    league: str
    home_team: str
    away_team: str
    match_date: date
    match_time: Optional[datetime] = None
    handicap: Optional[str] = None

    # 胜平负
    odds_home_win: Optional[float] = None
    odds_draw: Optional[float] = None
    odds_away_win: Optional[float] = None

    # 让球胜平负
    odds_hhad_home_win: Optional[float] = None
    odds_hhad_draw: Optional[float] = None
    odds_hhad_away_win: Optional[float] = None

    # 支持率
    support_home: Optional[float] = None
    support_draw: Optional[float] = None
    support_away: Optional[float] = None

    # 比分赔率 { "1:0": 9.5, ... }
    score_odds: Optional[dict] = None
    # 总进球数赔率 { "0": 11.0, "1": 4.7, ... }
    total_goals_odds: Optional[dict] = None
    # 半全场赔率 { "胜/胜": 4.7, ... }
    half_full_odds: Optional[dict] = None


def _normalize_text(text: Optional[str]) -> str:
    return " ".join(text.split()) if text else ""


def _extract_date_from_row(row: Tag) -> Optional[date]:
    td = row.find("td", class_="bDateTd")
    if not td:
        return None
    text = _normalize_text(td.get_text())
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def _extract_match_id(td: Tag) -> Optional[str]:
    text = _normalize_text(td.get_text())
    m = re.search(r"^(\D+)(\d+)$", text)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    parts = text.split()
    if len(parts) >= 2 and parts[-1].isdigit():
        return f"{parts[0]}{parts[-1]}"
    return None


def _extract_league(td: Tag) -> str:
    return _normalize_text(td.get_text())


def _parse_match_time(td: Tag, default_year: int) -> Optional[datetime]:
    """解析比赛时间。页面显示为北京时间，直接以北京时间（naive datetime）存储。"""
    text = _normalize_text(td.get_text())
    m = re.search(r"(\d{2})-(\d{2})\s*(\d{2}):(\d{2})", text)
    if not m:
        return None
    month, day, hour, minute = map(int, m.groups())
    try:
        return datetime(default_year, month, day, hour, minute)
    except ValueError:
        return None


def _extract_teams_and_mid(td: Tag) -> Optional[tuple]:
    text = _normalize_text(td.get_text())
    if "VS" not in text.upper():
        return None
    parts = re.split(r"\s*VS\s*", text, flags=re.IGNORECASE)
    if len(parts) != 2:
        return None
    home = re.sub(r"\[.*?\]", "", parts[0]).strip()
    away = re.sub(r"\[.*?\]", "", parts[1]).strip()

    mid = None
    vs_link = td.find("a", class_="vsA", href=True)
    if vs_link:
        href = vs_link["href"]
        m = re.search(r"mid=(\d+)", href)
        if m:
            mid = m.group(1)
    return home, away, mid


def _extract_handicap(td: Tag) -> Optional[str]:
    """非让球盘口（通常是 0）。"""
    div = td.find("div", class_="hadGL")
    if not div:
        return None
    text = _normalize_text(div.get_text())
    m = re.search(r"([+-]?\d+)", text)
    return m.group(1) if m else text


def _extract_handicap_line(td: Tag) -> Optional[str]:
    """让球盘口（如 +1 / -1）。"""
    div = td.find("div", class_="hhadGL")
    if not div:
        return None
    text = _normalize_text(div.get_text())
    m = re.search(r"([+-]?\d+)", text)
    return m.group(1) if m else text


def _extract_odds(td: Tag, odds_class: str = "hadOdds") -> Optional[tuple]:
    div = td.find("div", class_=odds_class)
    if not div:
        return None
    spans = div.find_all("span", class_="oddsItem")
    if len(spans) < 3:
        return None
    try:
        return (
            float(_normalize_text(spans[0].get_text())),
            float(_normalize_text(spans[1].get_text())),
            float(_normalize_text(spans[2].get_text())),
        )
    except ValueError:
        return None


def _extract_support(td: Tag, support_class: str = "hadU") -> Optional[tuple]:
    div = td.find("div", class_=support_class)
    if not div:
        return None
    spans = div.find_all("span")
    if len(spans) < 3:
        return None
    values = []
    for span in spans[:3]:
        text = _normalize_text(span.get_text()).replace("%", "")
        if text in ("", "--"):
            values.append(None)
            continue
        try:
            values.append(float(text))
        except ValueError:
            return None
    return tuple(values)


def _parse_match_row(row: Tag, default_date: date) -> Optional[ParsedMatch]:
    tds = row.find_all("td")
    if len(tds) < 8:
        return None

    match_id = _extract_match_id(tds[0])
    if not match_id:
        return None

    league = _extract_league(tds[1])
    teams = _extract_teams_and_mid(tds[3])
    if not teams:
        return None
    home_team, away_team, mid = teams

    match_time = _parse_match_time(tds[2], default_date.year)
    match_date = match_time.date() if match_time else default_date

    odds = _extract_odds(tds[5], odds_class="hadOdds")
    hhad_odds = _extract_odds(tds[5], odds_class="hhadOdds")
    support = _extract_support(tds[7], support_class="hadU")
    hhad_support = _extract_support(tds[7], support_class="hhadU")

    return ParsedMatch(
        match_id=match_id,
        mid=mid,
        league=league,
        home_team=home_team,
        away_team=away_team,
        match_date=match_date,
        match_time=match_time,
        handicap=_extract_handicap_line(tds[4]),
        odds_home_win=odds[0] if odds else None,
        odds_draw=odds[1] if odds else None,
        odds_away_win=odds[2] if odds else None,
        odds_hhad_home_win=hhad_odds[0] if hhad_odds else None,
        odds_hhad_draw=hhad_odds[1] if hhad_odds else None,
        odds_hhad_away_win=hhad_odds[2] if hhad_odds else None,
        support_home=support[0] if support else None,
        support_draw=support[1] if support else None,
        support_away=support[2] if support else None,
    )


def parse_lottery_matches(html: str) -> List[ParsedMatch]:
    """解析中国体彩竞彩足球赛程页面 HTML。"""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="mainTbl")
    if not table:
        logger.warning("mainTbl not found, trying generic table search")
        tables = soup.find_all("table")
        for t in tables:
            if t.find("td", class_="bDateTd"):
                table = t
                break

    if not table:
        logger.error("No schedule table found")
        return []

    matches: List[ParsedMatch] = []
    current_date: Optional[date] = None

    for row in table.find_all("tr"):
        date_from_row = _extract_date_from_row(row)
        if date_from_row:
            current_date = date_from_row
            continue

        if "listTr" not in (row.get("class") or []):
            continue

        if not current_date:
            continue

        match = _parse_match_row(row, current_date)
        if match:
            matches.append(match)

    logger.info("Parsed %d matches", len(matches))
    return matches


# ---------------------------------------------------------------------------
# 赛果开奖页解析（https://www.lottery.gov.cn/jc/zqsgkj/）
# ---------------------------------------------------------------------------


class ParsedResult(BaseModel):
    """从体彩赛果页解析出的单场结果。"""

    match_id: str
    mid: Optional[str] = None
    match_date: date
    league: str
    home_team: str
    away_team: str
    half_time_score: Optional[str] = None
    full_time_score: Optional[str] = None
    status: str = ""


def _extract_result_match_id(td: Tag) -> Optional[str]:
    """从赛果页行单元格提取赛事编号，如 周五202。"""
    text = _normalize_text(td.get_text())
    m = re.search(r"^(\D+)(\d+)$", text)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    parts = text.split()
    if len(parts) >= 2 and parts[-1].isdigit():
        return f"{parts[0]}{parts[-1]}"
    return None


def _extract_result_teams_and_mid(td: Tag) -> Optional[tuple]:
    """从赛果页对阵单元格提取主客队、mid。"""
    link = td.find("a", href=True)
    if not link:
        return None
    text = _normalize_text(link.get_text())
    if "VS" not in text.upper():
        return None
    parts = re.split(r"\s*VS\s*", text, flags=re.IGNORECASE)
    if len(parts) != 2:
        return None
    # 去掉让球盘口如 (-1)、(+1)
    home = re.sub(r"\s*[（(][+-]?\d+(\.\d+)?[）)]\s*", "", parts[0]).strip()
    away = re.sub(r"\s*[（(][+-]?\d+(\.\d+)?[）)]\s*", "", parts[1]).strip()

    href = link["href"]
    m = re.search(r"mid=(\d+)", href)
    mid = m.group(1) if m else None
    return home, away, mid


def _extract_score_text(td: Tag) -> Optional[str]:
    """提取比分文本，如 2:0。"""
    text = _normalize_text(td.get_text())
    if not text or text in ("--", ""):
        return None
    m = re.match(r"^(\d+)\s*:\s*(\d+)$", text)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    return None


def _extract_status_text(td: Tag) -> str:
    return _normalize_text(td.get_text())


def _parse_result_row(row: Tag) -> Optional[ParsedResult]:
    """解析赛果页的一行数据。"""
    tds = row.find_all("td")
    if len(tds) < 10:
        return None

    # 某些页面把日期和编号放在同一格，兼容处理
    match_id = _extract_result_match_id(tds[1]) or _extract_result_match_id(tds[0])
    if not match_id:
        return None

    date_text = _normalize_text(tds[0].get_text())
    m = re.search(r"(\d{4}-\d{2}-\d{2})", date_text)
    if not m:
        return None
    try:
        match_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None

    league = _extract_league(tds[2])
    teams = _extract_result_teams_and_mid(tds[3])
    if not teams:
        return None
    home_team, away_team, mid = teams

    return ParsedResult(
        match_id=match_id,
        mid=mid,
        match_date=match_date,
        league=league,
        home_team=home_team,
        away_team=away_team,
        half_time_score=_extract_score_text(tds[4]),
        full_time_score=_extract_score_text(tds[5]),
        status=_extract_status_text(tds[9]) if len(tds) > 9 else "",
    )


def parse_match_results(html: str) -> List[ParsedResult]:
    """解析中国体彩足球赛果开奖页面 HTML，返回已结束比赛结果列表。"""
    soup = BeautifulSoup(html, "lxml")

    # 优先定位动态渲染的结果表格（#matchList 内的 table）
    match_list = soup.find("div", id="matchList")
    table = match_list.find("table") if match_list else None
    if not table:
        # 兜底：取页面中数据行最多的 table
        tables = soup.find_all("table")
        best_table = None
        best_count = 0
        for t in tables:
            data_rows = [
                r for r in t.find_all("tr")
                if len(r.find_all("td")) >= 10 and not r.find("th")
            ]
            if len(data_rows) > best_count:
                best_count = len(data_rows)
                best_table = t
        table = best_table

    if not table:
        logger.error("Results page: no table found")
        return []

    results: List[ParsedResult] = []
    for row in table.find_all("tr"):
        # 跳过表头行
        if row.find("th"):
            continue
        result = _parse_result_row(row)
        if result:
            results.append(result)

    logger.info("Parsed %d match results", len(results))
    return results


# ---------------------------------------------------------------------------
# 其它玩法赔率解析（比分、总进球、半全场）
# ---------------------------------------------------------------------------


def _extract_match_id_from_row(row: Tag) -> Optional[str]:
    """从 listTr 行的第一个 td 提取编号。"""
    tds = row.find_all("td")
    if not tds:
        return None
    return _extract_match_id(tds[0])


def _api_crs_key_to_score(key: str) -> Optional[str]:
    """把体彩 API 的 crs 字段 key 转换成比分赔率标签。

    体彩 crs key 格式为 s0Hs0A，其中 H 为主队进球、A 为客队进球。
    示例：
        s01s00 -> 1:0
        s00s01 -> 0:1
        s02s01 -> 2:1
        s1sa   -> 负其它
        s1sd   -> 平其它
        s1sh   -> 胜其它
    """
    if key == "s1sa":
        return "负其它"
    if key == "s1sd":
        return "平其它"
    if key == "s1sh":
        return "胜其它"
    m = re.match(r"s(\d)(\d)s(\d)(\d)$", key)
    if not m:
        return None
    return f"{m.group(2)}:{m.group(4)}"


def parse_score_odds(html: str) -> Dict[str, dict]:
    """解析比分页面，返回 {match_id: {比分: 赔率}}。"""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="mainTbl")
    if not table:
        logger.error("Score page: mainTbl not found")
        return {}

    result: Dict[str, dict] = {}
    current_match_id: Optional[str] = None

    for row in table.find_all("tr"):
        cls = row.get("class") or []
        if "listTr" in cls:
            current_match_id = _extract_match_id_from_row(row)
            continue

        if "crsOddsTr" not in cls or not current_match_id:
            continue

        odds_table = row.find("table", class_="crsOdds")
        if not odds_table:
            continue

        score_map: Dict[str, float] = {}
        for tr in odds_table.find_all("tr"):
            for item in tr.find_all("span", class_="oddsItem"):
                div = item.find("div")
                if not div:
                    continue
                score_text = _normalize_text(div.get_text())
                odds_text = _normalize_text(item.get_text().replace(score_text, "", 1))
                try:
                    score_map[score_text] = float(odds_text)
                except ValueError:
                    continue

        if score_map:
            result[current_match_id] = score_map

    logger.info("Parsed score odds for %d matches", len(result))
    return result


_WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _business_date_to_weekday_cn(business_date: str) -> str:
    """把 businessDate（如 2026-07-26）转成中文星期。"""
    try:
        dt = datetime.strptime(business_date, "%Y-%m-%d")
        return _WEEKDAY_CN[dt.weekday()]
    except ValueError:
        return ""


def parse_score_odds_from_api(api_response: dict) -> Dict[str, dict]:
    """解析体彩统一接口返回的比分赔率数据。

    接口示例：
        https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry?channel=c&poolCode=crs

    返回：{match_id: {比分: 赔率}}
    """
    result: Dict[str, dict] = {}
    value = api_response.get("value") if isinstance(api_response, dict) else None
    if not value:
        logger.warning("Score odds API response has no value")
        return result

    for day_info in value.get("matchInfoList", []):
        weekday = day_info.get("businessDateCn") or _business_date_to_weekday_cn(
            day_info.get("businessDate", "")
        )
        for match in day_info.get("subMatchList", []):
            match_num = match.get("matchNum")
            crs = match.get("crs")
            if not match_num or not crs:
                continue
            # matchNum 如 7202，需要加上星期前缀 -> "周日202"
            match_num_str = str(match_num)
            if weekday and match_num_str.isdigit():
                match_id = f"{weekday}{match_num_str[1:]}"
            else:
                match_id = match_num_str

            score_map: Dict[str, float] = {}
            for key, val in crs.items():
                score = _api_crs_key_to_score(key)
                if score is None:
                    continue
                try:
                    score_map[score] = float(val)
                except (ValueError, TypeError):
                    continue

            if score_map:
                result[match_id] = score_map

    logger.info("Parsed score odds from API for %d matches", len(result))
    return result


def parse_total_goals_odds(html: str) -> Dict[str, dict]:
    """解析总进球数页面，返回 {match_id: {进球数: 赔率}}。"""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="mainTbl")
    if not table:
        logger.error("Total goals page: mainTbl not found")
        return {}

    result: Dict[str, dict] = {}
    goals_labels = ["0", "1", "2", "3", "4", "5", "6", "7+"]

    for row in table.find_all("tr"):
        if "listTr" not in (row.get("class") or []):
            continue

        match_id = _extract_match_id_from_row(row)
        if not match_id:
            continue

        td = row.find("td", class_="ttgOdds")
        if not td:
            continue

        spans = td.find_all("span", class_="oddsItem")
        goals_map: Dict[str, float] = {}
        for i, span in enumerate(spans[: len(goals_labels)]):
            text = _normalize_text(span.get_text())
            try:
                goals_map[goals_labels[i]] = float(text)
            except ValueError:
                continue

        if goals_map:
            result[match_id] = goals_map

    logger.info("Parsed total goals odds for %d matches", len(result))
    return result


def parse_half_full_odds(html: str) -> Dict[str, dict]:
    """解析半全场页面，返回 {match_id: {半全场结果: 赔率}}。"""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="mainTbl")
    if not table:
        logger.error("Half-full page: mainTbl not found")
        return {}

    result: Dict[str, dict] = {}
    hf_labels = ["胜/胜", "胜/平", "胜/负", "平/胜", "平/平", "平/负", "负/胜", "负/平", "负/负"]

    for row in table.find_all("tr"):
        if "listTr" not in (row.get("class") or []):
            continue

        match_id = _extract_match_id_from_row(row)
        if not match_id:
            continue

        td = row.find("td", class_="hafuOdds")
        if not td:
            continue

        spans = td.find_all("span", class_="oddsItem")
        hf_map: Dict[str, float] = {}
        for i, span in enumerate(spans[: len(hf_labels)]):
            text = _normalize_text(span.get_text())
            try:
                hf_map[hf_labels[i]] = float(text)
            except ValueError:
                continue

        if hf_map:
            result[match_id] = hf_map

    logger.info("Parsed half-full odds for %d matches", len(result))
    return result
