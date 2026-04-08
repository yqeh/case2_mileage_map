"""Excel parsing and export helpers."""

from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger
from openpyxl import load_workbook

from utils.path_manager import get_output_dir


class ExcelService:
    """Handle Excel parsing, grouping, and export updates."""

    def __init__(self):
        self.required_columns = [
            '部門',
            '姓名',
            '計畫別',
            '起點名稱',
            '出差日期時間（開始）',
            '出差日期時間（結束）',
            '目的地名稱',
        ]

    def _get_sort_key(self, date_value):
        if date_value is None:
            return datetime.min
        if isinstance(date_value, str):
            try:
                return pd.to_datetime(date_value)
            except Exception:
                return datetime.min
        if isinstance(date_value, pd.Timestamp):
            if pd.isna(date_value):
                return datetime.min
            return date_value.to_pydatetime()
        if isinstance(date_value, datetime):
            return date_value
        return datetime.min

    def parse_excel(self, file_path):
        try:
            logger.info(f"開始讀取 Excel 檔案: {file_path}")
            df = pd.read_excel(file_path, engine='openpyxl')
            logger.info(f"Excel 檔案讀取完成，共 {len(df)} 行, {len(df.columns)} 欄")

            column_mapping = {
                '部門': '部門',
                '姓名': '姓名',
                '計畫別': '計畫別',
                'ProjectName': '計畫別',
                '起點名稱': '起點名稱',
                '起點地址': '起點地址',
                'StartAddress': '起點地址',
                '出差日期時間（開始）': '出差日期時間（開始）',
                '出差日期時間（結束）': '出差日期時間（結束）',
                '目的地名稱': '目的地名稱',
                '終點地址': '終點地址',
                'EndAddress': '終點地址',
                '連結': '連結',
                'Link': '連結',
            }
            rename_map = {src: dst for src, dst in column_mapping.items() if src in df.columns}
            df = df.rename(columns=rename_map)

            missing_columns = [col for col in self.required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'success': False,
                    'error': f"缺少必要欄位: {', '.join(missing_columns)}",
                    'data': None,
                }

            for date_col in ('出差日期時間（開始）', '出差日期時間（結束）'):
                if date_col in df.columns:
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

            for old_col in ('IsDriving', '是否自駕'):
                if old_col in df.columns:
                    df = df.drop(columns=[old_col])

            # 新上傳資料預設走開車模式。
            df['IsDriving'] = 'Y'
            df['OneWayKm'] = None
            df['RoundTripKm'] = None
            df['GoogleMapUrl'] = None
            df['StaticMapImage'] = None
            df['StepCount'] = None
            df['Polyline'] = None
            df['RouteSteps'] = None

            records = []
            for _, row in df.iterrows():
                record = {}
                for col in df.columns:
                    value = row[col]
                    if pd.isna(value):
                        record[col] = None
                    elif isinstance(value, pd.Timestamp):
                        record[col] = value.isoformat()
                    else:
                        record[col] = value
                records.append(record)

            logger.info(f"成功解析 Excel 檔案: {len(records)} 筆資料")
            return {
                'success': True,
                'data': records,
                'total_count': len(records),
            }
        except Exception as e:
            logger.error(f"解析 Excel 檔案錯誤: {str(e)}")
            return {
                'success': False,
                'error': f"解析 Excel 檔案失敗: {str(e)}",
                'data': None,
            }

    def group_by_project(self, records):
        try:
            grouped = {}
            for record in records:
                project_name = record.get('計畫別', '未分類')
                grouped.setdefault(project_name, []).append(record)

            for project_name in grouped:
                grouped[project_name].sort(
                    key=lambda item: self._get_sort_key(item.get('出差日期時間（開始）')),
                    reverse=False,
                )

            logger.info(f"成功分組: {len(grouped)} 個計畫別")
            return grouped
        except Exception as e:
            logger.error(f"分組錯誤: {str(e)}")
            return {}

    def add_calculation_results(self, file_path, records):
        try:
            wb = load_workbook(file_path)
            ws = wb.active

            headers = [cell.value for cell in ws[1]]
            new_columns = [
                'OneWayKm',
                'RoundTripKm',
                'GoogleMapUrl',
                'StaticMapImage',
                'IsDriving',
                'StepCount',
                'Polyline',
                'RouteSteps',
            ]
            for col in new_columns:
                if col not in headers:
                    headers.append(col)
                    ws.cell(row=1, column=len(headers), value=col)

            col_index = {col: idx + 1 for idx, col in enumerate(headers)}

            for row_idx, record in enumerate(records, start=2):
                for key in new_columns:
                    value = record.get(key)
                    if value not in (None, ''):
                        ws.cell(row=row_idx, column=col_index[key], value=value)

            output_dir = get_output_dir()
            output_filename = f"updated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            output_path = Path(output_dir) / output_filename
            wb.save(str(output_path))
            logger.info(f"成功產生更新 Excel 檔案: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"更新 Excel 檔案錯誤: {str(e)}")
            raise
