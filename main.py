from PyQt5.QtWidgets import QApplication
from gui import TestGUI
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_window = TestGUI()
    test_window.show()
    sys.exit(app.exec())