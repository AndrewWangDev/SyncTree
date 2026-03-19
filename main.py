import sys
import os
from PySide6.QtWidgets import QApplication
from ui.window import MainWindow

def main():
    # run from the script directory for config.json!
    # and please replace the path(config.json) to your own computer os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    app = QApplication(sys.argv)
    
    # Optional styling or High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough) if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy') else None
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    from PySide6.QtCore import Qt
    main()
