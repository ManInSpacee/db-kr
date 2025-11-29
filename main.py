import sys
import logging
from PySide6.QtWidgets import QApplication
from gui import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
#sldhflkdsflkdsjflk
def main():
    app = QApplication(sys.argv)
    
    # Создаем главное окно
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
