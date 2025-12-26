import sys
import os

# PyInstaller 환경에서의 경로 설정 (Import 전에 실행되어야 함)
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_path)

from PyQt6.QtWidgets import QApplication
# Explicit imports to ensure PyInstaller bundles them
import src.ui.styles
import src.ui.widgets
import src.core.settings
import src.core.worker
from src.ui.main_window import PDFMasterApp

def main():
    app = QApplication(sys.argv)
    window = PDFMasterApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
