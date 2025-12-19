"""
第二案：地點里程與地圖報表系統 - 主應用程式
"""
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
from loguru import logger

# 載入環境變數
load_dotenv()

# 初始化 Flask 應用程式
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-here')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False

# 資料庫設定
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URI',
    'mysql+pymysql://user:password@localhost/mileage_map'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化擴充功能（從 extensions 導入以避免循環導入）
from extensions import db, jwt
db.init_app(app)
jwt.init_app(app)
CORS(app)

# 設定日誌
logger.add(
    "logs/app.log",
    rotation="1 day",
    retention="30 days",
    level="INFO",
    encoding="utf-8"
)

# 註冊藍圖
from api import auth, mileage, reports, settings
from routes import upload_bp, calculate_bp, export_bp

app.register_blueprint(auth.bp, url_prefix='/api/auth')
app.register_blueprint(mileage.bp, url_prefix='/api/mileage')
app.register_blueprint(reports.bp, url_prefix='/api/reports')
app.register_blueprint(settings.bp, url_prefix='/api/settings')

# 新功能路由
app.register_blueprint(upload_bp, url_prefix='/api/upload')
app.register_blueprint(calculate_bp, url_prefix='/api/calculate')
app.register_blueprint(export_bp, url_prefix='/api/export')

# 匯入模型以建立資料表
from models import User, TravelRecord, SystemSetting

@app.route('/')
def index():
    """API 根路徑"""
    return {
        'status': 'success',
        'message': '地點里程與地圖報表系統 API',
        'version': '1.0.0'
    }

@app.route('/health', methods=['GET'])
def health():
    """簡單健康檢查 API"""
    return {'status': 'ok'}, 200

@app.route('/temp/maps/<path:filename>')
def serve_map_image(filename):
    """提供靜態地圖圖片"""
    from flask import send_from_directory
    import os
    maps_dir = os.path.join('temp', 'maps')
    if os.path.exists(os.path.join(maps_dir, filename)):
        return send_from_directory(maps_dir, filename)
    else:
        return {'error': '檔案不存在'}, 404

@app.route('/api/health')
def health_detailed():
    """詳細健康檢查（包含資料庫狀態）"""
    try:
        # 嘗試連線資料庫（如果資料庫未設定，會失敗但不影響服務）
        db_status = 'connected'
        try:
            db.engine.connect()
        except:
            db_status = 'disconnected'
        
        return {
            'status': 'healthy',
            'database': db_status
        }
    except Exception as e:
        return {
            'status': 'healthy',
            'database': 'unknown',
            'note': 'Database check failed, but service is running'
        }

if __name__ == '__main__':
    # 建立必要目錄
    os.makedirs('temp/maps', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # 建立資料表（如果資料庫連線失敗，跳過此步驟）
    try:
        with app.app_context():
            db.create_all()
            logger.info("資料表初始化完成")
    except Exception as e:
        logger.warning(f"資料表初始化失敗（可能資料庫未連線）: {str(e)}")
    
    # 啟動應用程式
    port = int(os.getenv('PORT', 5001))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"啟動 Flask 服務在 http://{host}:{port}")
    logger.info(f"健康檢查: http://localhost:{port}/health")
    
    app.run(
        host=host,
        port=port,
        debug=debug
    )

