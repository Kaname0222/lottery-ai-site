import asyncio
import re
import time
import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from app.config import settings

logger = logging.getLogger(__name__)


def create_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=settings.SCRAPER_RETRY_TIMES,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update(
        {
            "User-Agent": settings.SCRAPER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
    )
    return session


def fetch_html(url: str, timeout: Optional[int] = None) -> Optional[str]:
    """使用 requests 抓取指定 URL 的 HTML 文本，失败返回 None。"""
    session = create_session()
    timeout = timeout or settings.SCRAPER_REQUEST_TIMEOUT
    try:
        logger.info("Fetching %s", url)
        resp = session.get(url, timeout=timeout)
        resp.encoding = resp.apparent_encoding or "utf-8"
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return None
    finally:
        session.close()


async def fetch_html_with_playwright(
    url: str,
    wait_ms: int = 3000,
    wait_selector: Optional[str] = "#mainTbl",
    wait_timeout: int = 30000,
) -> Optional[str]:
    """使用 Playwright 渲染页面后返回 HTML（带 stealth 反检测）。

    Args:
        url: 目标地址。
        wait_ms: 页面加载后额外等待的毫秒数。
        wait_selector: 等待渲染的选择器，None 表示不等待特定元素。
        wait_timeout: 等待选择器的超时时间（毫秒）。
    """
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth.stealth import Stealth
    except ImportError as exc:
        logger.error("Playwright/stealth not installed: %s", exc)
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            logger.info("Playwright fetching %s", url)
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=wait_timeout)
                    logger.info("Element %s rendered", wait_selector)
                except Exception as exc:
                    logger.warning("Element %s not rendered in time: %s", wait_selector, exc)
            await asyncio.sleep(wait_ms / 1000)
            html = await page.content()
            await browser.close()
            return html
    except Exception as exc:
        logger.error("Playwright fetch failed for %s: %s", url, exc)
        return None


def fetch_html_rendered(
    url: str,
    wait_ms: int = 3000,
    wait_selector: Optional[str] = "#mainTbl",
    wait_timeout: int = 30000,
) -> Optional[str]:
    """同步接口：使用 Playwright 渲染页面。"""
    return asyncio.run(
        fetch_html_with_playwright(
            url, wait_ms=wait_ms, wait_selector=wait_selector, wait_timeout=wait_timeout
        )
    )


def fetch_score_odds_via_api() -> Optional[dict]:
    """通过体彩统一接口获取当前在售比赛的比分赔率数据。

    该接口返回 JSON，比 Playwright 渲染页面更稳定。若请求失败返回 None，
    调用方可回退到 fetch_score_odds_html。
    """
    url = "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry"
    params = {"channel": "c", "poolCode": "crs"}
    headers = {
        "User-Agent": settings.SCRAPER_USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://www.lottery.gov.cn/",
    }
    session = create_session()
    try:
        logger.info("Fetching score odds via API %s", url)
        resp = session.get(url, params=params, headers=headers, timeout=settings.SCRAPER_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success") and data.get("value"):
            return data
        logger.warning("Score odds API returned empty value: %s", data.get("errorMessage"))
        return None
    except Exception as exc:
        logger.error("Score odds API fetch failed: %s", exc)
        return None
    finally:
        session.close()


async def fetch_score_odds_html(
    url: str,
    wait_ms: int = 3000,
    wait_timeout: int = 30000,
) -> Optional[str]:
    """使用 Playwright 渲染比分赔率页，并展开所有折叠行以加载完整赔率。

    比分赔率页默认只展开第一行，其余 .crsOddsTr 行 display:none，
    需要点击每行的 .folderTd 才能异步加载赔率。
    """
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth.stealth import Stealth
    except ImportError as exc:
        logger.error("Playwright/stealth not installed: %s", exc)
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            logger.info("Playwright fetching score odds %s", url)
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_selector("#mainTbl", timeout=wait_timeout)

            # 展开所有折叠行，触发赔率异步加载
            buttons = await page.query_selector_all("span.folderTd")
            for btn in buttons:
                try:
                    await btn.click()
                except Exception:
                    pass
            await asyncio.sleep(wait_ms / 1000)

            html = await page.content()
            await browser.close()
            return html
    except Exception as exc:
        logger.error("Playwright score odds fetch failed for %s: %s", url, exc)
        return None


def fetch_json(url: str, timeout: Optional[int] = None) -> Optional[dict]:
    """抓取 JSON 接口。"""
    session = create_session()
    timeout = timeout or settings.SCRAPER_REQUEST_TIMEOUT
    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("Failed to fetch json %s: %s", url, exc)
        return None
    finally:
        session.close()


def safe_float(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    text = text.strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None
