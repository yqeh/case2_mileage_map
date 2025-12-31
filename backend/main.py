"""
Case 2: 地點里程與地圖報表系統 - 整合啟動程式
- 本機/EXE：可自動開瀏覽器
- Render：不開瀏覽器、host=0.0.0.0、PORT 由環境變數提供
- 前端：用 repo 根目錄的 index.html、css/、js/、template.xlsx
"""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

from flask import Flask, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from loguru import logger

# =========================
# Path / mode
# =========================
IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    BASE_DIR = Path(sys._MEIPASS)            # PyInstaller 解包後目錄
    FRONTEND_DIR = BASE_DIR                  # 你打包時把前端放進同層
else:
    BASE_DIR = Path(__file__).parent         # .../backend
    FRONTEND_DIR = BASE_DIR.parent           # repo 根目錄（index.html 在這）

sys.path.insert(0, str(BASE_DIR))

# =========================
# .env：EXE 可用；Render 通常用 Dashboard env vars
# =========================
if IS_FROZEN:
    env_path = Path(sys.executable).parent / ".env"
    template_path = BASE_DIR / "env_template.txt"

    # exe 才會自動從 template 建 .env
    if (not env_path.exists()) and template_path.exists():
        import shutil
        shutil.copy(template_path, env_path)
        logger.info(f"已從 {template_path} 建立 .env 檔案")
else:
    env_path = BASE_DIR / ".env"

if env_path.exists():
    load_dotenv(env_path)

# =========================
# Flask app
# =========================
app = Flask(__name__, static_folder=None, template_folder=None)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "your-secret-key-here")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-here")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False

# =========================
# DB
# =========================
database_uri = os.getenv("DATABASE_URI", "").strip()
if not database_uri:
    if IS_FROZEN:
        db_path = Path(sys.executable).parent / "mileage_map.db"
    else:
        db_path = BASE_DIR / "mileage_map.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    logger.info(f"未設定 DATABASE_URI，使用 SQLite：{db_path}")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# =========================
# Extensions
# =========================
from extensions import db, jwt
db.init_app(app)
jwt.init_app(app)

# =========================
# CORS（同網域其實不一定需要，但保留）
# =========================
port = int(os.getenv("PORT", "5001"))
allowed_origins = [
    f"http://localhost:{port}",
    f"http://127.0.0.1:{port}",
]
frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip()
if frontend_origin:
    allowed_origins.append(frontend_origin)

CORS(
    app,
    resources={r"/api/*": {"origins": allowed_origins}},
    supports_credentials=False,
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    vary_header=True,
)

# =========================
# Logging
# =========================
if IS_FROZEN:
    logs_dir = Path(sys.executable).parent / "logs"
else:
    logs_dir = BASE_DIR / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

logger.add(
    str(logs_dir / "app.log"),
    rotation="1 day",
    retention="30 days",
    level="INFO",
    encoding="utf-8",
)

# =========================
# Blueprints
# =========================
from api import auth, mileage, reports, settings
from routes import upload_bp, calculate_bp, export_bp

app.register_blueprint(auth.bp, url_prefix="/api/auth")
app.register_blueprint(mileage.bp, url_prefix="/api/mileage")
app.register_blueprint(reports.bp, url_prefix="/api/reports")
app.register_blueprint(settings.bp, url_prefix="/api/settings")
app.register_blueprint(upload_bp, url_prefix="/api/upload")
app.register_blueprint(calculate_bp, url_prefix="/api/calculate")
app.register_blueprint(export_bp, url_prefix="/api/export")

from models import User, TravelRecord, SystemSetting  # noqa: F401

# =========================
# Required dirs
# =========================
if IS_FROZEN:
    base_data_dir = Path(sys.executable).parent
    temp_maps_dir = base_data_dir / "temp" / "maps"
    output_dir = base_data_dir / "output"
else:
    temp_maps_dir = BASE_DIR / "temp" / "maps"
    output_dir = BASE_DIR / "output"

temp_maps_dir.mkdir(parents=True, exist_ok=True)
output_dir.mkdir(parents=True, exist_ok=True)

# =========================
# Frontend routes
# =========================
@app.get("/")
def index():
    # 你已經把 excel-upload.html 改名 index.html
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.get("/template")
def download_template():
    # 你說「Excel 檔」= 範本下載（template.xlsx）
    return send_from_directory(
        FRONTEND_DIR,
        "template.xlsx",
        as_attachment=True,
        download_name="template.xlsx",
    )

@app.get("/<path:filename>")
def serve_frontend(filename: str):
    if filename.endswith(".html"):
        return send_from_directory(FRONTEND_DIR, filename)

    if filename.startswith("css/"):
        css_file = filename.replace("css/", "", 1)
        return send_from_directory(FRONTEND_DIR / "css", css_file)

    if filename.startswith("js/"):
        js_file = filename.replace("js/", "", 1)
        return send_from_directory(FRONTEND_DIR / "js", js_file)

    if filename == "favicon.ico":
        f = FRONTEND_DIR / "favicon.ico"
        if f.exists():
            return send_from_directory(FRONTEND_DIR, "favicon.ico")
        return ("", 204)

    return {"error": "檔案不存在"}, 404

# =========================
# Map images
# =========================
@app.get("/temp/maps/<path:filename>")
def serve_map_image(filename):
    if (temp_maps_dir / filename).exists():
        return send_from_directory(str(temp_maps_dir), filename)
    return {"error": "檔案不存在"}, 404

# =========================
# Health checks
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}, 200

@app.get("/api/health")
def health_detailed():
    try:
        db_status = "connected"
        try:
            db.engine.connect()
        except Exception:
            db_status = "disconnected"
        return {"status": "healthy", "database": db_status}
    except Exception:
        return {"status": "healthy", "database": "unknown"}

# =========================
# EXE only: open browser
# =========================
def open_browser():
    time.sleep(1.5)
    port = int(os.getenv("PORT", "5001"))
    url = f"http://localhost:{port}/"
    webbrowser.open(url)
    logger.info(f"已自動打開瀏覽器: {url}")

# =========================
# Entry
# =========================
if __name__ == "__main__":
    try:
        with app.app_context():
            db.create_all()
            logger.info("資料表初始化完成")
    except Exception as e:
        logger.warning(f"資料表初始化失敗: {str(e)}")

    # exe 才開瀏覽器；Render 不開
    if IS_FROZEN:
        threading.Thread(target=open_browser, daemon=True).start()

    port = int(os.getenv("PORT", "5001"))
    is_cloud = bool(os.getenv("RENDER")) or (not IS_FROZEN and os.getenv("PORT") is not None)
    host = "0.0.0.0" if is_cloud else os.getenv("HOST", "127.0.0.1")
    debug = os.getenv("DEBUG", "False").lower() == "true"

    logger.info(f"啟動服務在 http://{host}:{port}")
    logger.info(f"前端頁面: http://{host}:{port}/")

    app.run(host=host, port=port, debug=debug, use_reloader=False)
