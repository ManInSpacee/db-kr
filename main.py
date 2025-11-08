"""
Главный файл приложения
Запускает графический интерфейс
"""
import sys
import logging
from PySide6.QtWidgets import QApplication
from gui import MainWindow

# Настройка логирования
# Логи пишутся в файл app.log и выводятся в консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)


def main():
    """
    Главная функция приложения
    Создает приложение Qt и главное окно
    """
    # Создаем приложение Qt
    app = QApplication(sys.argv)
    
    # Создаем главное окно
    window = MainWindow()
    window.show()
    
    # Запускаем цикл обработки событий
    # Приложение будет работать пока не закроется
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
