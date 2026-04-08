"""
Excel 上傳與起點/終點地址解析測試
驗證：匯入檔案可讀取起點地址、終點地址欄位；上傳 API 正常回傳
"""
import os
import sys
import tempfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

# 確保 backend 在 path（conftest 已 insert 上一層，此處備援）
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from services.excel_service import ExcelService


@pytest.fixture
def excel_service():
    """Excel 服務實例"""
    return ExcelService()


@pytest.fixture
def temp_excel_with_addresses():
    """建立含起點地址、終點地址的暫存 Excel"""
    df = pd.DataFrame({
        "部門": ["安環處", "安環處"],
        "姓名": ["張三", "李四"],
        "計畫別": ["測試計畫", "測試計畫"],
        "起點名稱": ["辦公室", "辦公室"],
        "起點地址": ["高雄市前鎮區復興四路12號", "高雄市前鎮區復興四路12號"],
        "出差日期時間（開始）": ["2024-10-22 09:00", "2024-10-23 09:00"],
        "出差日期時間（結束）": ["2024-10-22 17:00", "2024-10-23 17:00"],
        "目的地名稱": ["客戶端", "客戶端"],
        "終點地址": ["高雄市苓雅區四維三路2號", "高雄市苓雅區四維三路2號"],
    })
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    df.to_excel(path, index=False, engine="openpyxl")
    yield path
    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture
def temp_excel_without_addresses():
    """僅有起點名稱、目的地名稱的 Excel（無地址欄）"""
    df = pd.DataFrame({
        "部門": ["安環處"],
        "姓名": ["王五"],
        "計畫別": ["計畫A"],
        "起點名稱": ["安環高雄處"],
        "出差日期時間（開始）": ["2024-10-22 09:00"],
        "出差日期時間（結束）": ["2024-10-22 17:00"],
        "目的地名稱": ["經濟部產業園區管理局"],
    })
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    df.to_excel(path, index=False, engine="openpyxl")
    yield path
    try:
        os.unlink(path)
    except Exception:
        pass


class TestExcelParseAddressColumns:
    """測試 Excel 解析起點地址、終點地址"""

    def test_parse_excel_with_起點地址_終點地址(
        self, excel_service, temp_excel_with_addresses
    ):
        """有起點地址、終點地址欄位時，解析結果應包含該欄位"""
        result = excel_service.parse_excel(temp_excel_with_addresses)
        assert result["success"] is True
        assert result["total_count"] == 2
        data = result["data"]
        assert len(data) == 2
        for record in data:
            assert record.get("起點地址") == "高雄市前鎮區復興四路12號"
            assert record.get("終點地址") == "高雄市苓雅區四維三路2號"
            assert record.get("起點名稱") == "辦公室"
            assert record.get("目的地名稱") == "客戶端"

    def test_parse_excel_without_address_columns(
        self, excel_service, temp_excel_without_addresses
    ):
        """無起點地址、終點地址時，仍可解析，且不報錯"""
        result = excel_service.parse_excel(temp_excel_without_addresses)
        assert result["success"] is True
        assert result["total_count"] == 1
        record = result["data"][0]
        assert record.get("起點名稱") == "安環高雄處"
        assert record.get("目的地名稱") == "經濟部產業園區管理局"
        # 無欄位時 get 為 None
        assert record.get("起點地址") is None
        assert record.get("終點地址") is None

    def test_group_by_project_includes_addresses(
        self, excel_service, temp_excel_with_addresses
    ):
        """分組後每筆紀錄仍保留起點地址、終點地址"""
        parse_result = excel_service.parse_excel(temp_excel_with_addresses)
        assert parse_result["success"] is True
        grouped = excel_service.group_by_project(parse_result["data"])
        assert "測試計畫" in grouped
        for record in grouped["測試計畫"]:
            assert record.get("起點地址") == "高雄市前鎮區復興四路12號"
            assert record.get("終點地址") == "高雄市苓雅區四維三路2號"


class TestUploadApi:
    """上傳 API 整合測試（需 test_client）"""

    def test_upload_excel_with_address_columns_returns_data(
        self, test_client, temp_excel_with_addresses
    ):
        """上傳含起點地址、終點地址的 Excel，API 回傳的 records 應包含該欄位"""
        with open(temp_excel_with_addresses, "rb") as f:
            file_bytes = f.read()
        data = {
            "file": (Path(temp_excel_with_addresses).name, BytesIO(file_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            "fixed_origin": "",
        }
        response = test_client.post(
            "/api/upload/excel",
            data=data,
        )
        assert response.status_code == 200, response.get_data(as_text=True)
        body = response.get_json()
        assert body.get("status") == "success"
        projects = body.get("data", {}).get("projects", {})
        assert "測試計畫" in projects
        records = projects["測試計畫"]["records"]
        assert len(records) == 2
        for record in records:
            assert record.get("起點地址") == "高雄市前鎮區復興四路12號"
            assert record.get("終點地址") == "高雄市苓雅區四維三路2號"
