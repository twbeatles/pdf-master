import sys
import os
import logging
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler

# 로그 파일 경로
LOG_FILE = os.path.join(os.path.expanduser("~"), ".pdf_master.log")

def setup_logging():
    """로깅 설정 초기화 (v4.5: 로그 파일 순환 적용)"""
    # v4.5: RotatingFileHandler로 로그 파일 무한 증가 방지
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, stream_handler]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# PyInstaller 환경에서의 경로 설정 (Import 전에 실행되어야 함)
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_path)

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication, QFont
# Explicit imports to ensure PyInstaller bundles them
import src.ui.styles
import src.ui.widgets
import src.core.settings
import src.core.worker
from src.ui.main_window import PDFMasterApp

def global_exception_handler(exc_type, exc_value, exc_tb):
    """전역 예외 핸들러 - 처리되지 않은 예외를 로그에 기록"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.critical(f"Uncaught exception:\n{error_msg}")
    
    # 사용자에게 오류 알림 (QApplication이 존재하는 경우)
    app = QApplication.instance()
    if app:
        QMessageBox.critical(
            None, 
            "오류 발생",
            f"예상치 못한 오류가 발생했습니다.\n\n{exc_value}\n\n상세 로그: {LOG_FILE}"
        )

def main():
    # 전역 예외 핸들러 설정
    sys.excepthook = global_exception_handler
    
    # HiDPI 지원 활성화
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    logger.info("PDF Master starting...")
    
    try:
        app = QApplication(sys.argv)
        app.setFont(QFont("Segoe UI", 9))  # Windows 기본 폰트 크기 설정
        window = PDFMasterApp()
        window.show()
        logger.info("PDF Master ready")
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Failed to start application: {e}")
        raise

if __name__ == "__main__":
    main()
