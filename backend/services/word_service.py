"""
Word 報表產生服務
"""
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from datetime import datetime
from loguru import logger
from utils.path_manager import get_output_dir
from utils.log_sanitizer import sanitize_filename
import os


class WordService:
    """Word 報表產生服務類別"""

    def __init__(self):
        self.output_dir = get_output_dir()

    def _format_km(self, value):
        """
        格式化公里數（與 mileage_report_demo 一致）
        - 若為整數，顯示整數（例如：19）
        - 否則顯示一位小數（例如：19.1）
        
        Args:
            value: 公里數值（float 或 int）
        
        Returns:
            str: 格式化後的公里數字串
        """
        try:
            # 轉換為 float
            km = float(value) if value is not None else 0.0
            
            # 判斷是否為整數
            if km == int(km):
                return str(int(km))
            else:
                return f"{km:.1f}"
                
        except Exception as e:
            logger.error(f"公里數格式化失敗: {e}")
            return str(value) if value is not None else "0"

    def _format_mmdd(self, date_value):
        """
        將日期格式化為 M/D 格式（不含前導 0）
        參考 mileage_report_demo 的格式
        
        Args:
            date_value: datetime 物件或字串
        
        Returns:
            str: M/D 格式的日期字串（例如：7/12、10/22）
        """
        try:
            if not date_value:
                return ""

            if isinstance(date_value, datetime):
                dt = date_value
            elif isinstance(date_value, str):
                try:
                    dt = datetime.strptime(date_value, '%Y-%m-%d')
                except ValueError:
                    try:
                        dt = datetime.fromisoformat(date_value)
                    except ValueError:
                        logger.warning(f"無法解析日期字串: {date_value}")
                        return str(date_value)
            else:
                logger.warning(f"不支援的日期類型: {type(date_value)}")
                return str(date_value)

            # 格式化為 M/D（不含前導 0）
            month = dt.month
            day = dt.day
            return f"{month}/{day}"

        except Exception as e:
            logger.error(f"日期格式化失敗: {e}")
            return str(date_value)

    def _safe_dt(self, date_value):
        """
        取得可排序的 datetime，避免 NoneType 比較錯誤。

        Args:
            date_value: datetime 或字串或 None

        Returns:
            datetime: 可用於排序的 datetime
        """
        if not date_value:
            return datetime.min

        if isinstance(date_value, datetime):
            return date_value

        if isinstance(date_value, str):
            # 允許 YYYY-MM-DD、ISO 格式、或含時間的 ISO 格式
            try:
                return datetime.fromisoformat(date_value)
            except ValueError:
                try:
                    return datetime.strptime(date_value, "%Y-%m-%d")
                except ValueError:
                    logger.warning(f"無法解析日期字串，改用 datetime.min: {date_value}")
                    return datetime.min

        logger.warning(f"不支援的日期類型，改用 datetime.min: {type(date_value)}")
        return datetime.min

    def _pick_km(self, record):
        """
        取得可用的里程欄位（支援多種欄位命名）。

        優先順序（由高到低）：
        - RoundTripKm / round_trip_km
        - 自駕里程 / self_drive_km / is_self_drive_km
        - 公里數 / DistanceKm / distance_km
        - OneWayKm / one_way_km

        Args:
            record: 單筆紀錄 dict

        Returns:
            float | int | str | None: 原始里程值（交由 _format_km 處理）
        """
        candidates = [
            "RoundTripKm",
            "round_trip_km",
            "自駕里程",
            "self_drive_km",
            "is_self_drive_km",
            "公里數",
            "DistanceKm",
            "distance_km",
            "OneWayKm",
            "one_way_km",
        ]

        for key in candidates:
            if key in record and record.get(key) not in (None, ""):
                return record.get(key)

        return 0
    
    def generate_report(self, project_name, records, fixed_origin=None, page_break_per_record=True):
        """
        產生 Word 報表（與 mileage_report_demo 一致）
        
        Args:
            project_name: 計畫別名稱
            records: 該計畫別的紀錄列表（需包含計算結果）
            fixed_origin: 固定起點地址（可選）
            page_break_per_record: 是否每筆記錄換頁（預設 True，與 mileage_report_demo 一致）
            
        Returns:
            str: Word 檔案路徑
        """
        try:
            # 建立 Word 文件
            doc = Document()

            # 依日期排序
            sorted_records = sorted(
                records,
                key=lambda x: self._safe_dt(x.get("出差日期時間（開始）")),
                reverse=False
            )

            # 處理每筆紀錄
            for idx, record in enumerate(sorted_records):
                try:
                    logger.info(f"處理第 {idx + 1}/{len(sorted_records)} 筆記錄")

                    # 第二筆開始換頁（與 mileage_report_demo 一致）
                    if idx > 0:
                        doc.add_page_break()

                    # 取得資料
                    travel_date = record.get('出差日期時間（開始）')
                    date_str = self._format_mmdd(travel_date)

                    # 起點和終點
                    origin_name = record.get('起點名稱', '')
                    destination_name = record.get('目的地名稱', '')

                    # 使用固定起點或原始起點
                    if fixed_origin:
                        origin_display = fixed_origin
                    else:
                        origin_display = origin_name

                    # 取得完整地址（用於標題，包含郵遞區號）
                    origin_address = (
                        record.get('OriginAddress') or
                        record.get('起點地址') or
                        record.get('origin_address') or
                        origin_display
                    )
                    destination_address = (
                        record.get('DestinationAddress') or
                        record.get('終點地址') or
                        record.get('destination_address') or
                        destination_name
                    )

                    # 里程（核銷/自駕里程）：欄位名容錯處理
                    km_value = self._pick_km(record)

                    # 格式化公里數
                    km_str = self._format_km(km_value)

                    # 建立標題 - 格式：7/12804 高雄市鼓山區裕誠路1091號至832 高雄市林園區石化二路10號往返,核銷62公里。
                    # 根據圖片，標題應包含完整地址（含郵遞區號）
                    title_text = (
                        f"{date_str}{origin_address}至{destination_address}往返,"
                        f"核銷{km_str}公里。"
                    )

                    logger.debug(f"  標題: {title_text}")

                    # 加入標題段落
                    title_paragraph = doc.add_paragraph(title_text)
                    title_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT

                    # 設定標題格式（加粗、字體大小 18pt，與 mileage_report_demo 一致）
                    for run in title_paragraph.runs:
                        run.bold = True
                        run.font.size = Pt(18)

                    # 標題下方新增自駕里程行（14pt）
                    drive_km_paragraph = doc.add_paragraph(f"自駕里程：{km_str} 公里")
                    drive_km_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    for run in drive_km_paragraph.runs:
                        run.font.size = Pt(14)
                    
                    # 插入 Google Maps 路線截圖（完整截圖，包含左側面板和右側地圖）
                    map_image_path = record.get('StaticMapImage')
                    absolute_image_path = None

                    if map_image_path:
                        # 處理相對路徑（前面可能有 /）
                        from utils.path_manager import get_base_dir
                        base_dir = get_base_dir()

                        # 移除前面的 /
                        clean_path = map_image_path.lstrip('/')
                        # 轉換為絕對路徑
                        absolute_image_path = base_dir / clean_path

                        # 檢查檔案是否存在且大小 > 10KB
                        if absolute_image_path.exists():
                            file_size = os.path.getsize(absolute_image_path)
                            if file_size <= 10240:  # 10KB
                                logger.warning(f"  地圖圖片檔案太小 ({file_size} bytes): {absolute_image_path}")
                                absolute_image_path = None
                        else:
                            logger.warning(f"  地圖圖片檔案不存在: {absolute_image_path}")
                            absolute_image_path = None

                    if absolute_image_path:
                        try:
                            logger.debug(f"  插入圖片: {absolute_image_path}")
                            picture_paragraph = doc.add_paragraph()
                            picture_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            run = picture_paragraph.add_run()
                            # 使用 6.5 英吋寬度（與 mileage_report_demo 一致）
                            run.add_picture(str(absolute_image_path), width=Inches(6.5))
                        except Exception as e:
                            logger.error(f"  插入圖片失敗: {e}")
                            # 插入錯誤提示文字
                            error_paragraph = doc.add_paragraph()
                            error_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            error_run = error_paragraph.add_run("本筆地圖截圖失敗")
                            error_run.font.size = Pt(14)
                    else:
                        logger.warning(f"  沒有有效的地圖圖片: {map_image_path}")
                        # 插入錯誤提示文字
                        error_paragraph = doc.add_paragraph()
                        error_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        error_run = error_paragraph.add_run("本筆地圖截圖失敗")
                        error_run.font.size = Pt(14)

                except Exception as e:
                    logger.error(f"處理第 {idx + 1} 筆記錄時發生錯誤: {e}")
                    # 繼續處理下一筆
                    continue

            # 儲存檔案
            project_display_name = project_name or "未分類"
            # 允許中文計畫別並清理不合法檔名字元，
            # 避免不同計畫別被覆寫成同一個檔案
            filename = sanitize_filename(f"{project_display_name}_里程報表.docx")
            if not filename:
                filename = "未分類_里程報表.docx"
            file_path = self.output_dir / filename

            try:
                doc.save(str(file_path))
                logger.info(f"報表已儲存: {str(file_path)}")
                return str(file_path)
            except Exception as e:
                logger.error(f"儲存報表失敗: {e}")
                raise

        except Exception as e:
            logger.error(f"產生 Word 報表錯誤: {str(e)}")
            raise

    # 移除不需要的方法（與 mileage_report_demo 一致，不使用表格）
