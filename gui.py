"""
Графический интерфейс приложения
"""
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QDialog, QFormLayout, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QDateEdit
)
from PySide6.QtCore import QDate
from db import create_schema, insert_data, get_data
from config import ATTACK_TYPES
from alter_dialog import AlterTableDialog
from advanced_view_dialog import AdvancedViewDialog


class InputDialog(QDialog):
    """
    Модальное окно для ввода данных эксперимента
    
    Модальное окно блокирует родительское окно до закрытия
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить данные")
        self.setModal(True)  # Блокируем родительское окно
        self.setMinimumWidth(300)
        
        # Создаем форму для ввода
        layout = QFormLayout()
        
        # Поле для названия эксперимента
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: Тест SYN атаки")
        layout.addRow("Название:", self.name_edit)
        
        # Выпадающий список для выбора типа атаки
        # Используем те же типы что и в БД
        self.attack_combo = QComboBox()
        self.attack_combo.addItems(ATTACK_TYPES)
        layout.addRow("Тип атаки:", self.attack_combo)
        
        # Поле для количества пакетов
        self.packets_edit = QLineEdit()
        self.packets_edit.setPlaceholderText("Например: 1000")
        layout.addRow("Пакетов:", self.packets_edit)
        
        # Поле для длительности
        self.duration_edit = QLineEdit()
        self.duration_edit.setPlaceholderText("Например: 10.5")
        layout.addRow("Длительность (сек):", self.duration_edit)
        
        # Поле для даты
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())  # По умолчанию сегодня
        self.date_edit.setCalendarPopup(True)  # Показываем календарь
        layout.addRow("Дата:", self.date_edit)
        
        # Кнопки
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)  # Закрываем окно без сохранения
        
        # Основной layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(btn_save)
        main_layout.addWidget(btn_cancel)
        self.setLayout(main_layout)
    
    def validate_data(self):
        """
        Проверить корректность введенных данных
        
        Returns:
            Список ошибок (пустой если все ОК)
        """
        errors = []
        
        # Получаем значения из полей
        name = self.name_edit.text().strip()
        packets = self.packets_edit.text().strip()
        duration = self.duration_edit.text().strip()
        
        # Проверка 1: Название
        if not name:
            errors.append("Поле 'Название' не заполнено")
        elif len(name) > 255:
            errors.append(f"Поле 'Название' слишком длинное (максимум 255 символов, введено {len(name)})")
        
        # Проверка 2: Пакеты (должно быть целое число)
        if not packets:
            errors.append("Поле 'Пакетов' не заполнено")
        else:
            try:
                packets_int = int(packets)
                if packets_int <= 0:
                    errors.append("Поле 'Пакетов' должно быть больше 0")
                elif packets_int > 2147483647:  # Максимум для INTEGER в PostgreSQL
                    errors.append(f"Поле 'Пакетов' слишком большое (максимум 2147483647, введено {packets_int})")
            except ValueError:
                errors.append(f"Поле 'Пакетов' должно быть целым числом (введено: '{packets}')")
        
        # Проверка 3: Длительность (должно быть число)
        if not duration:
            errors.append("Поле 'Длительность' не заполнено")
        else:
            try:
                duration_float = float(duration)
                if duration_float <= 0:
                    errors.append("Поле 'Длительность' должно быть больше 0")
                elif duration_float > 99999999.99:  # Максимум для DECIMAL(10,2)
                    errors.append(f"Поле 'Длительность' слишком большое (максимум 99999999.99, введено {duration_float})")
            except ValueError:
                errors.append(f"Поле 'Длительность' должно быть числом (введено: '{duration}')")
        
        return errors
    
    def save(self):
        """Сохранить данные в базу"""
        # Валидация данных перед сохранением
        errors = self.validate_data()
        
        # Если есть ошибки - показываем их все
        if errors:
            error_text = "Обнаружены ошибки:\n\n"
            for i, error in enumerate(errors, 1):
                error_text += f"{i}. {error}\n"
            QMessageBox.warning(self, "Ошибки ввода", error_text)
            return
        
        # Если валидация прошла - получаем значения
        name = self.name_edit.text().strip()
        attack_type = self.attack_combo.currentText()
        packets = self.packets_edit.text().strip()
        duration = self.duration_edit.text().strip()
        date = self.date_edit.date().toString("yyyy-MM-dd")
        
        # Пытаемся сохранить данные
        try:
            success, msg = insert_data(name, attack_type, packets, duration, date)
            if success:
                QMessageBox.information(self, "Успех", msg)
                self.accept()  # Закрываем окно с успехом
            else:
                QMessageBox.critical(self, "Ошибка", msg)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")


class ViewDialog(QDialog):
    """
    Окно для просмотра данных с фильтрами
    
    Модальное окно для отображения таблицы с данными
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Просмотр данных")
        self.setModal(True)  # Блокируем родительское окно
        self.setMinimumSize(800, 500)
        
        layout = QVBoxLayout()
        
        # Секция фильтров
        filter_layout = QFormLayout()
        
        # Фильтр по типу атаки
        # Используем те же типы что и в БД
        self.attack_filter = QComboBox()
        self.attack_filter.addItem("Все", None)  # Первый элемент - "Все" (без фильтра)
        self.attack_filter.addItems(ATTACK_TYPES)  # Добавляем все типы атак
        filter_layout.addRow("Тип атаки:", self.attack_filter)
        
        # Фильтр по дате начала
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))  # По умолчанию -30 дней
        self.date_from.setCalendarPopup(True)  # Показываем календарь
        filter_layout.addRow("Дата от:", self.date_from)
        
        # Фильтр по дате окончания
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())  # По умолчанию сегодня
        self.date_to.setCalendarPopup(True)
        filter_layout.addRow("Дата до:", self.date_to)
        
        # Кнопка применения фильтров
        btn_apply = QPushButton("Применить")
        btn_apply.clicked.connect(self.load_data)
        
        layout.addLayout(filter_layout)
        layout.addWidget(btn_apply)
        
        # Таблица для отображения данных
        self.table = QTableWidget()
        layout.addWidget(self.table)
        
        # Кнопка закрытия
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
        
        self.setLayout(layout)
        
        # Загружаем данные при открытии окна
        self.load_data()
    
    def load_data(self):
        """Загрузить данные из БД с применением фильтров"""
        # Получаем значения фильтров
        attack_type = self.attack_filter.currentData()  # None если выбрано "Все"
        
        # Получаем даты (можем передать None если не нужны фильтры)
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        
        # Получаем данные из БД
        data = get_data(attack_type, date_from, date_to)
        
        # Настраиваем таблицу
        self.table.setColumnCount(6)  # 6 столбцов
        self.table.setHorizontalHeaderLabels([
            "ID", "Название", "Тип атаки", "Пакетов", "Длительность", "Дата"
        ])
        self.table.setRowCount(len(data))
        
        # Заполняем таблицу данными
        for row, record in enumerate(data):
            for col, value in enumerate(record):
                # Форматируем дату для лучшего отображения
                if col == 5 and value:  # Столбец с датой
                    if isinstance(value, str):
                        # Если это строка, оставляем как есть
                        display_value = value
                    else:
                        # Если это datetime объект, форматируем
                        display_value = str(value)
                else:
                    display_value = str(value) if value is not None else ""
                
                self.table.setItem(row, col, QTableWidgetItem(display_value))
        
        # Автоматически подгоняем ширину столбцов
        self.table.resizeColumnsToContents()
        
        # Показываем сообщение если данных нет
        if len(data) == 0:
            QMessageBox.information(self, "Информация", "Данные не найдены. Попробуйте изменить фильтры.")


class MainWindow(QMainWindow):
    """
    Главное окно приложения
    
    Содержит три кнопки:
    1. Создать базу - создает схему и таблицы
    2. Внести данные - открывает модальное окно ввода
    3. Показать данные - открывает модальное окно просмотра
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DDoS Эксперименты")
        self.setGeometry(100, 100, 400, 280)
        
        # Центральный виджет
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Кнопка 1: Создать базу
        btn_create = QPushButton("Создать базу")
        btn_create.clicked.connect(self.on_create)
        layout.addWidget(btn_create)
        
        # Кнопка 2: Внести данные
        btn_insert = QPushButton("Внести данные")
        btn_insert.clicked.connect(self.on_insert)
        layout.addWidget(btn_insert)
        
        # Кнопка 3: Показать данные
        btn_view = QPushButton("Показать данные")
        btn_view.clicked.connect(self.on_view)
        layout.addWidget(btn_view)
        
        # Кнопка 4: Изменить структуру (ALTER TABLE)
        btn_alter = QPushButton("Изменить структуру")
        btn_alter.clicked.connect(self.on_alter)
        layout.addWidget(btn_alter)
        
        # Кнопка 5: Расширенный просмотр
        btn_advanced = QPushButton("Расширенный просмотр")
        btn_advanced.clicked.connect(self.on_advanced)
        layout.addWidget(btn_advanced)
    
    def on_create(self):
        """Обработчик нажатия кнопки 'Создать базу'"""
        success, msg = create_schema()
        if success:
            QMessageBox.information(self, "Успех", msg)
        else:
            QMessageBox.critical(self, "Ошибка", msg)
    
    def on_insert(self):
        """Обработчик нажатия кнопки 'Внести данные'"""
        # Открываем модальное окно ввода
        dialog = InputDialog(self)
        dialog.exec()  # Блокируем выполнение до закрытия окна
    
    def on_view(self):
        """Обработчик нажатия кнопки 'Показать данные'"""
        # Открываем модальное окно просмотра
        dialog = ViewDialog(self)
        dialog.exec()  # Блокируем выполнение до закрытия окна
    
    def on_alter(self):
        """Обработчик нажатия кнопки 'Изменить структуру'"""
        dialog = AlterTableDialog(self)
        dialog.exec()
    
    def on_advanced(self):
        """Обработчик нажатия кнопки 'Расширенный просмотр'"""
        dialog = AdvancedViewDialog(self)
        dialog.exec()

