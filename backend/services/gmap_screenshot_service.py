"""Google Maps screenshot helpers."""

from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse
import asyncio
import os
import re

from loguru import logger

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright 未安裝，無法進行 Google Maps 截圖")


def _extract_dir_segments_from_path(path: str) -> list[str]:
    parts = path.split('/maps/dir/', 1)
    if len(parts) != 2:
        return []

    remainder = parts[1]
    for marker in ('/@', '/data=', '?', '#'):
        remainder = remainder.split(marker, 1)[0]

    return [segment for segment in remainder.split('/') if segment]


def normalize_google_maps_driving_url(maps_url: str) -> str:
    """Force a Google Maps route URL into driving mode when possible."""
    if not maps_url:
        return maps_url

    try:
        parsed = urlparse(maps_url)
        host = (parsed.netloc or '').lower()
        if 'google.' not in host or '/maps/dir' not in parsed.path:
            return maps_url

        segments = _extract_dir_segments_from_path(parsed.path)
        if len(segments) >= 2:
            origin = segments[0]
            destination = segments[-1]
            waypoints = segments[1:-1]
            query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
            query = {
                'api': '1',
                'origin': origin,
                'destination': destination,
                'travelmode': 'driving',
            }
            for key, value in query_pairs:
                if key not in query:
                    query[key] = value
            if waypoints:
                query['waypoints'] = '|'.join(waypoints)

            return urlunparse((
                parsed.scheme or 'https',
                parsed.netloc,
                '/maps/dir/',
                '',
                urlencode(query, doseq=False),
                '',
            ))

        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if query.get('api') == '1':
            query['travelmode'] = 'driving'
            return urlunparse((
                parsed.scheme or 'https',
                parsed.netloc,
                parsed.path,
                '',
                urlencode(query, doseq=False),
                '',
            ))
    except Exception as e:
        logger.warning(f"Google Maps 連結轉開車模式失敗，改用原始連結: {e}")

    return maps_url


def extract_distance_km_from_text(text: str) -> Optional[float]:
    """Extract the first visible Google Maps route distance from page text."""
    if not text:
        return None

    # Prefer kilometer values. Meter values also appear in the map scale and are
    # not reliable route distances, so they are intentionally ignored.
    patterns = [
        r'([0-9]+(?:[.,][0-9]+)?)\s*\u516c\u91cc',
        r'([0-9]+(?:[.,][0-9]+)?)\s*km\b',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            try:
                value = float(match.group(1).replace(',', '.'))
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
    return None


async def capture_maps_url_screenshot(
    maps_url: str,
    output_path: str | Path,
    viewport_width: int = 1366,
    viewport_height: int = 768,
    wait_timeout: int = 30000,
    log_context: str | None = None,
    metadata: dict | None = None,
) -> Optional[str]:
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright 未安裝，無法進行 Google Maps 截圖")
        return None

    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        maps_url = normalize_google_maps_driving_url(maps_url)
        logger.info(f"開始截取 Google Maps 路線: {log_context or maps_url}")
        logger.debug(f"Google Maps URL: {maps_url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ],
            )
            try:
                context = await browser.new_context(
                    viewport={'width': viewport_width, 'height': viewport_height},
                    device_scale_factor=2,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                )
                try:
                    page = await context.new_page()
                    logger.debug(f"導航到 Google Maps: {maps_url}")
                    await page.goto(maps_url, wait_until='domcontentloaded', timeout=wait_timeout)
                    logger.debug('頁面 domcontentloaded 完成')

                    try:
                        logger.debug('等待 canvas 或 main 元素...')
                        await page.wait_for_selector('canvas, div[role="main"]', timeout=15000)
                        logger.debug('檢測到 canvas 或 main 元素')
                    except PlaywrightTimeoutError:
                        logger.warning('等待主要地圖元素逾時，改以目前畫面截圖')

                    await page.wait_for_timeout(3000)
                    if metadata is not None:
                        try:
                            page_text = await page.locator('body').inner_text(timeout=10000)
                            distance_km = extract_distance_km_from_text(page_text)
                            if distance_km:
                                metadata['distance_km'] = distance_km
                                logger.debug(f"? Google Maps ???????: {distance_km}")
                        except Exception as e:
                            logger.warning(f"? Google Maps ?????????: {e}")
                    logger.debug(f"Viewport 尺寸: {page.viewport_size}")
                    await page.wait_for_timeout(1000)
                    logger.debug(f"開始截圖，儲存到: {output_path}")
                    await page.screenshot(path=str(output_path), full_page=False, type='png')
                    logger.debug('截圖完成')
                finally:
                    await context.close()
            finally:
                await browser.close()
                await asyncio.sleep(0.5)

        if not output_path.exists():
            logger.error(f"截圖檔案不存在: {output_path}")
            return None

        file_size = os.path.getsize(output_path)
        if file_size <= 10240:
            logger.error(f"截圖檔案過小 ({file_size} bytes): {output_path}")
            try:
                output_path.unlink(missing_ok=True)
            except Exception:
                pass
            return None

        logger.info(f"成功截取 Google Maps 路線截圖: {output_path} ({file_size} bytes)")
        return str(output_path)
    except PlaywrightTimeoutError as e:
        logger.error(f"Google Maps 截圖逾時: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Google Maps 截圖失敗: {str(e)}")
        return None


async def capture_route_screenshot(
    origin: str,
    destination: str,
    output_path: str | Path,
    viewport_width: int = 1366,
    viewport_height: int = 768,
    wait_timeout: int = 30000,
) -> Optional[str]:
    origin_encoded = quote(origin)
    destination_encoded = quote(destination)
    maps_url = (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={origin_encoded}"
        f"&destination={destination_encoded}"
        f"&travelmode=driving"
    )
    return await capture_maps_url_screenshot(
        maps_url=maps_url,
        output_path=output_path,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        wait_timeout=wait_timeout,
        log_context=f"{origin} -> {destination}",
    )


def _run_async(coro, wait_timeout: int):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=(wait_timeout / 1000) + 30)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def capture_maps_url_screenshot_sync(
    maps_url: str,
    output_path: str | Path,
    viewport_width: int = 1366,
    viewport_height: int = 768,
    wait_timeout: int = 30000,
    log_context: str | None = None,
    metadata: dict | None = None,
) -> Optional[str]:
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright 未安裝，無法進行 Google Maps 截圖")
        return None
    try:
        return _run_async(
            capture_maps_url_screenshot(
                maps_url,
                output_path,
                viewport_width,
                viewport_height,
                wait_timeout,
                log_context,
                metadata,
            ),
            wait_timeout,
        )
    except Exception as e:
        logger.error(f"同步 Google Maps 截圖失敗: {str(e)}")
        return None


def capture_route_screenshot_sync(
    origin: str,
    destination: str,
    output_path: str | Path,
    viewport_width: int = 1366,
    viewport_height: int = 768,
    wait_timeout: int = 30000,
) -> Optional[str]:
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright 未安裝，無法進行 Google Maps 截圖")
        return None
    try:
        return _run_async(
            capture_route_screenshot(
                origin,
                destination,
                output_path,
                viewport_width,
                viewport_height,
                wait_timeout,
            ),
            wait_timeout,
        )
    except Exception as e:
        logger.error(f"同步路線截圖失敗: {str(e)}")
        return None
