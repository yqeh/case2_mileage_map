"""Word report generation service."""

from datetime import datetime
from pathlib import Path
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from services.gmap_screenshot_service import (
    capture_maps_url_screenshot_sync,
    capture_route_screenshot_sync,
)
from utils.log_sanitizer import sanitize_filename
from utils.path_manager import get_base_dir, get_output_dir, get_relative_path, get_temp_maps_dir


class WordService:
    """Generate Word reports for travel records."""

    def __init__(self):
        self.output_dir = get_output_dir()

    def _format_mmdd(self, date_value):
        try:
            if not date_value:
                return ""
            if isinstance(date_value, datetime):
                dt = date_value
            elif isinstance(date_value, str):
                try:
                    dt = datetime.strptime(date_value, '%Y-%m-%d')
                except ValueError:
                    dt = datetime.fromisoformat(date_value)
            else:
                return str(date_value)
            return f"{dt.month}/{dt.day}"
        except Exception:
            return str(date_value)

    def _safe_dt(self, date_value):
        if not date_value:
            return datetime.min
        if isinstance(date_value, datetime):
            return date_value
        if isinstance(date_value, str):
            try:
                return datetime.fromisoformat(date_value)
            except ValueError:
                try:
                    return datetime.strptime(date_value, "%Y-%m-%d")
                except ValueError:
                    return datetime.min
        return datetime.min

    def _load_font(self, size: int):
        candidates = [
            get_base_dir() / 'assets' / 'fonts' / 'NotoSansTC-Regular.ttf',
            Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'msjh.ttc',
            Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'mingliu.ttc',
        ]
        for fp in candidates:
            try:
                if str(fp).lower().endswith('.ttc'):
                    return ImageFont.truetype(str(fp), size, index=0)
                return ImageFont.truetype(str(fp), size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _resolve_existing_image(self, map_image_path):
        if not map_image_path:
            return None
        base_dir = get_base_dir()
        clean_path = str(map_image_path).lstrip('/\\')
        absolute_image_path = base_dir / clean_path
        if not absolute_image_path.exists():
            return None
        if os.path.getsize(absolute_image_path) <= 10240:
            return None
        return absolute_image_path

    def _stamp_timestamp(self, image_path: Path):
        now_text = datetime.now().strftime('截圖時間: %Y/%m/%d %H:%M')
        image = Image.open(image_path).convert('RGB')
        draw = ImageDraw.Draw(image)
        font = self._load_font(24)
        bbox = draw.textbbox((0, 0), now_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pad = 12
        x = image.width - text_w - pad * 2 - 20
        y = image.height - text_h - pad * 2 - 20
        draw.rounded_rectangle((x, y, x + text_w + pad * 2, y + text_h + pad * 2), radius=12, fill=(255, 255, 255))
        draw.text((x + pad, y + pad), now_text, fill=(40, 40, 40), font=font)
        image.save(image_path)

    def _capture_image_from_link(self, record):
        maps_url = record.get('連結') or record.get('GoogleMapUrl') or record.get('google_map_url')
        if not maps_url:
            return None
        temp_maps_dir = get_temp_maps_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        output_path = temp_maps_dir / f'word_link_{timestamp}.png'
        screenshot_path = capture_maps_url_screenshot_sync(
            maps_url=maps_url,
            output_path=str(output_path),
            viewport_width=1920,
            viewport_height=1080,
            wait_timeout=30000,
            log_context=record.get('目的地名稱') or record.get('終點地址') or 'Google Maps link',
        )
        if not screenshot_path:
            return None
        absolute_path = Path(screenshot_path)
        if not absolute_path.exists() or os.path.getsize(absolute_path) <= 10240:
            return None
        self._stamp_timestamp(absolute_path)
        relative_path = get_relative_path(absolute_path)
        if not relative_path.startswith('/'):
            relative_path = '/' + relative_path
        record['StaticMapImage'] = relative_path
        return absolute_path

    def _capture_image_from_route(self, origin_address, destination_address, record):
        if not origin_address or not destination_address:
            return None
        temp_maps_dir = get_temp_maps_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        output_path = temp_maps_dir / f'word_route_{timestamp}.png'
        screenshot_path = capture_route_screenshot_sync(
            origin=origin_address,
            destination=destination_address,
            output_path=str(output_path),
            viewport_width=1920,
            viewport_height=1080,
            wait_timeout=30000,
        )
        if not screenshot_path:
            return None
        absolute_path = Path(screenshot_path)
        if not absolute_path.exists() or os.path.getsize(absolute_path) <= 10240:
            return None
        self._stamp_timestamp(absolute_path)
        relative_path = get_relative_path(absolute_path)
        if not relative_path.startswith('/'):
            relative_path = '/' + relative_path
        record['StaticMapImage'] = relative_path
        return absolute_path

    def _record_owner_key(self, record):
        department = str(record.get('部門') or '').strip()
        employee = str(record.get('姓名') or '').strip()
        chain_group = str(record.get('RouteChainGroup') or '').strip()
        if department or employee or chain_group:
            return f'{department}::{employee}::{chain_group}'
        return ''

    def _pick_text(self, *values):
        for value in values:
            text = str(value or '').strip()
            if text:
                return text
        return ''

    def _resolve_locations(self, record, fixed_origin, last_stop_by_owner):
        owner_key = self._record_owner_key(record)
        disable_chain = str(record.get('DisableChainedOrigin') or '').strip().upper() == 'Y'
        chained_origin = '' if disable_chain else (last_stop_by_owner.get(owner_key) if owner_key else '')

        start_name = self._pick_text(record.get('起點名稱'))
        start_address = self._pick_text(
            record.get('起點地址'),
            record.get('OriginAddress'),
            record.get('origin_address'),
        )
        destination_name = self._pick_text(record.get('目的地名稱'))
        destination_address = self._pick_text(
            record.get('終點地址'),
            record.get('DestinationAddress'),
            record.get('destination_address'),
        )

        default_origin_display = self._pick_text(fixed_origin, start_name, start_address)
        default_origin_route = self._pick_text(fixed_origin, start_address, start_name)
        destination_display = self._pick_text(destination_name, destination_address)
        destination_route = self._pick_text(destination_address, destination_name)

        origin_display = self._pick_text(chained_origin, default_origin_display)
        origin_route = self._pick_text(chained_origin, default_origin_route)

        return owner_key, origin_display, origin_route, destination_display, destination_route

    def generate_report(self, project_name, records, fixed_origin=None, page_break_per_record=True):
        try:
            doc = Document()
            sorted_records = sorted(records, key=lambda x: self._safe_dt(x.get('出差日期時間（開始）')))
            last_stop_by_owner = {}

            for idx, record in enumerate(sorted_records):
                try:
                    logger.info(f"處理第 {idx + 1}/{len(sorted_records)} 筆記錄")
                    if idx > 0 and page_break_per_record:
                        doc.add_page_break()

                    date_str = self._format_mmdd(record.get('出差日期時間（開始）'))
                    owner_key, origin_display, origin_route, destination_display, destination_route = self._resolve_locations(
                        record,
                        fixed_origin,
                        last_stop_by_owner,
                    )

                    title_text = f"{date_str}{origin_display}至{destination_display}"
                    title_paragraph = doc.add_paragraph(title_text)
                    title_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    for run in title_paragraph.runs:
                        run.bold = True
                        run.font.size = Pt(18)

                    absolute_image_path = self._resolve_existing_image(record.get('StaticMapImage'))
                    if not absolute_image_path:
                        absolute_image_path = self._capture_image_from_route(origin_route, destination_route, record)
                    if not absolute_image_path:
                        absolute_image_path = self._capture_image_from_link(record)

                    if absolute_image_path:
                        picture_paragraph = doc.add_paragraph()
                        picture_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        run = picture_paragraph.add_run()
                        run.add_picture(str(absolute_image_path), width=Inches(6.5))
                    else:
                        error_paragraph = doc.add_paragraph()
                        error_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        error_run = error_paragraph.add_run('本筆地圖截圖失敗')
                        error_run.font.size = Pt(14)

                    if owner_key and destination_route:
                        last_stop_by_owner[owner_key] = destination_route
                except Exception as e:
                    logger.error(f"處理第 {idx + 1} 筆記錄時發生錯誤: {e}")
                    continue

            project_display_name = project_name or '未分類'
            filename = sanitize_filename(f"{project_display_name}_里程報表.docx") or '未分類_里程報表.docx'
            file_path = self.output_dir / filename
            doc.save(str(file_path))
            logger.info(f"報表已儲存: {str(file_path)}")
            return str(file_path)
        except Exception as e:
            logger.error(f"產生 Word 報表錯誤: {str(e)}")
            raise
