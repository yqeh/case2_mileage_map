"""
Google Maps 路線截圖服務
使用 Playwright 截取 Google Maps 完整路線頁面（包含左側面板和右側地圖）
"""
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from loguru import logger
import asyncio
import os

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright 未安裝，無法使用 Google Maps 截圖功能")


async def capture_maps_url_screenshot(
    maps_url: str,
    output_path: str | Path,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
    wait_timeout: int = 30000,
    log_context: str | None = None,
) -> Optional[str]:
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright 未安裝，無法截取 Google Maps 畫面")
        return None

    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"開始截取 Google Maps 路線: {log_context or maps_url}")
        logger.debug(f"Google Maps URL: {maps_url}")

        browser = None
        context = None
        page = None

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )

            try:
                context = await browser.new_context(
                    viewport={'width': viewport_width, 'height': viewport_height},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = await context.new_page()

                console_messages = []
                page_errors = []

                def handle_console(msg):
                    console_messages.append({
                        "type": msg.type,
                        "text": msg.text,
                        "location": str(msg.location) if hasattr(msg, 'location') else None,
                    })
                    logger.debug(f"[PLAYWRIGHT_CONSOLE] {msg.type}: {msg.text}")

                def handle_pageerror(error):
                    page_errors.append({
                        "message": str(error),
                        "stack": error.stack if hasattr(error, 'stack') else None,
                    })
                    logger.debug(f"[PLAYWRIGHT_PAGEERROR] {error}")

                page.on("console", handle_console)
                page.on("pageerror", handle_pageerror)

                try:
                    logger.debug(f"導航到 Google Maps: {maps_url}")
                    await page.goto(maps_url, wait_until="domcontentloaded", timeout=wait_timeout)
                    logger.debug("頁面 domcontentloaded 完成")

                    try:
                        logger.debug("等待 canvas 或 main 元素...")
                        await page.wait_for_selector('canvas, div[role="main"]', timeout=15000)
                        logger.debug("檢測到 canvas 或 main 元素")
                    except PlaywrightTimeoutError:
                        logger.warning("未檢測到 canvas 或 main 元素，繼續等待...")

                    await page.wait_for_timeout(3000)

                    viewport_size = page.viewport_size
                    if viewport_size and (viewport_size['width'] == 0 or viewport_size['height'] == 0):
                        logger.error(f"Viewport 尺寸異常: {viewport_size}")
                        return None
                    logger.debug(f"Viewport 尺寸: {viewport_size}")

                    await page.wait_for_timeout(1000)
                    logger.debug(f"開始截圖，儲存到: {output_path}")
                    await page.screenshot(path=str(output_path), full_page=False, type='png')
                    logger.debug("截圖完成")

                    if not os.path.exists(output_path):
                        logger.error(f"截圖檔案不存在: {output_path}")
                        return None

                    file_size = os.path.getsize(output_path)
                    if file_size <= 10240:
                        logger.error(f"截圖檔案太小 ({file_size} bytes)，可能截圖失敗: {output_path}")
                        try:
                            os.remove(output_path)
                        except Exception:
                            pass
                        return None

                    logger.info(f"成功截取 Google Maps 路線截圖: {output_path} ({file_size} bytes)")
                    return str(output_path)

                except PlaywrightTimeoutError as e:
                    logger.error(f"等待頁面載入超時: {str(e)}")
                    return None
                except Exception as e:
                    logger.error(f"截取 Google Maps 截圖時發生錯誤: {str(e)}")
                    import traceback
                    logger.debug(f"錯誤詳情: {traceback.format_exc()}")
                    return None
                finally:
                    if page:
                        try:
                            await page.close()
                        except Exception as e:
                            logger.warning(f"關閉 page 時發生錯誤: {str(e)}")
                    if context:
                        try:
                            await context.close()
                        except Exception as e:
                            logger.warning(f"關閉 context 時發生錯誤: {str(e)}")
            finally:
                if browser:
                    try:
                        await browser.close()
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.warning(f"關閉 browser 時發生錯誤: {str(e)}")
    except Exception as e:
        logger.error(f"Playwright 執行失敗: {str(e)}")
        import traceback
        logger.debug(f"錯誤詳情: {traceback.format_exc()}")
        return None


async def capture_route_screenshot(
    origin: str,
    destination: str,
    output_path: str | Path,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
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


def capture_maps_url_screenshot_sync(
    maps_url: str,
    output_path: str | Path,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
    wait_timeout: int = 30000,
    log_context: str | None = None,
) -> Optional[str]:
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright 未安裝，無法截取 Google Maps 畫面")
        return None
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        capture_maps_url_screenshot(maps_url, output_path, viewport_width, viewport_height, wait_timeout, log_context)
                    )
                    return future.result(timeout=(wait_timeout / 1000) + 30)
            return loop.run_until_complete(
                capture_maps_url_screenshot(maps_url, output_path, viewport_width, viewport_height, wait_timeout, log_context)
            )
        except RuntimeError:
            return asyncio.run(
                capture_maps_url_screenshot(maps_url, output_path, viewport_width, viewport_height, wait_timeout, log_context)
            )
    except Exception as e:
        logger.error(f"同步連結截圖函數執行失敗: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def capture_route_screenshot_sync(
    origin: str,
    destination: str,
    output_path: str | Path,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
    wait_timeout: int = 30000,
) -> Optional[str]:
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright 未安裝，無法截取 Google Maps 畫面")
        return None
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        capture_route_screenshot(origin, destination, output_path, viewport_width, viewport_height, wait_timeout)
                    )
                    return future.result(timeout=(wait_timeout / 1000) + 30)
            return loop.run_until_complete(
                capture_route_screenshot(origin, destination, output_path, viewport_width, viewport_height, wait_timeout)
            )
        except RuntimeError:
            return asyncio.run(
                capture_route_screenshot(origin, destination, output_path, viewport_width, viewport_height, wait_timeout)
            )
    except Exception as e:
        logger.error(f"同步截圖函數執行失敗: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None
