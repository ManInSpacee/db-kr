"""
Графический интерфейс приложения
"""
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QDialog, QFormLayout, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QDateEdit, QGroupBox
)
from PySide6.QtCore import QDate
from db import create_schema, drop_schema, insert_data, get_data, get_auxiliary_items
from config import ATTACK_TYPES
from alter_dialog import AlterTableDialog, COLUMN_LABELS
from advanced_view_dialog import AdvancedViewDialog
from db import get_table_columns, get_connection, get_auxiliary_items


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
        
        # Связь с вспомогательной таблицей
        self.aux_combo = QComboBox()
        self.aux_combo.addItem("Не выбрано", None)
        try:
            for item in get_auxiliary_items():
                display = f"{item['label']} · {item['segment_code']} ({item['criticality']})"
                self.aux_combo.addItem(display, item["id"])
        except Exception:
            pass
        layout.addRow("Связь (вспомогательная):", self.aux_combo)
        
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
        aux_id = self.aux_combo.currentData()
        
        # Пытаемся сохранить данные
        try:
            success, msg = insert_data(name, attack_type, packets, duration, date, aux_id)
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
        
        # Выбор таблицы
        self.table_selector = QComboBox()
        self.populate_tables()
        self.table_selector.currentIndexChanged.connect(self.load_data)
        layout.addWidget(self.table_selector)
        
        # Секция фильтров
        filter_layout = QFormLayout()
        
        # Фильтр по типу атаки
        # Используем те же типы что и в БД
        self.attack_filter = QComboBox()
        self.attack_filter.addItem("Все", None)
        for attack in ATTACK_TYPES:
            self.attack_filter.addItem(attack, attack)
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
        
        # Блок подзапросов
        self.setup_subquery_group(layout)
        
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

    def populate_tables(self):
        """Заполнить список таблиц для отображения и вернуть первый элемент."""
        self.table_selector.clear()
        conn = get_connection()
        tables = []
        if conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='ddos' AND table_type='BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            cur.close()
        if tables:
            for table in tables:
                self.table_selector.addItem(table, table)
            self.table_selector.setCurrentIndex(0)
            return tables[0]
        else:
            self.table_selector.addItem("experiments", "experiments")
            return "experiments"

    def setup_subquery_group(self, layout):
        group = QGroupBox("Фильтр с подзапросом")
        form = QFormLayout()
        
        self.subquery_type = QComboBox()
        self.subquery_type.addItem("Не использовать", None)
        self.subquery_type.addItem("EXISTS", "EXISTS")
        self.subquery_type.addItem("NOT EXISTS", "NOT EXISTS")
        self.subquery_type.addItem("ANY", "ANY")
        self.subquery_type.addItem("ALL", "ALL")
        form.addRow("Тип фильтра:", self.subquery_type)
        
        self.outer_column_combo = QComboBox()
        form.addRow("Колонка основной таблицы:", self.outer_column_combo)
        
        self.subquery_operator = QComboBox()
        self.subquery_operator.addItems(["=", "<>", ">", ">=", "<", "<="])
        form.addRow("Оператор:", self.subquery_operator)
        
        self.subquery_table_combo = QComboBox()
        self.subquery_table_combo.currentIndexChanged.connect(self.populate_subquery_columns)
        form.addRow("Таблица подзапроса:", self.subquery_table_combo)
        
        self.subquery_column_combo = QComboBox()
        form.addRow("Колонка подзапроса:", self.subquery_column_combo)
        
        self.subquery_link_column_combo = QComboBox()
        form.addRow("Колонка для связи:", self.subquery_link_column_combo)
        
        self.subquery_filter_column_combo = QComboBox()
        form.addRow("Фильтр по колонке:", self.subquery_filter_column_combo)
        
        self.subquery_filter_operator = QComboBox()
        self.subquery_filter_operator.addItems(["=", "<>", ">", ">=", "<", "<="])
        form.addRow("Оператор фильтра:", self.subquery_filter_operator)
        
        self.subquery_filter_value = QLineEdit()
        form.addRow("Значение фильтра:", self.subquery_filter_value)
        
        group.setLayout(form)
        layout.addWidget(group)
        
        self.populate_subquery_tables()
        self.subquery_type.currentIndexChanged.connect(self.update_subquery_controls)
        self.update_subquery_controls()

    def get_schema_tables(self):
        conn = get_connection()
        if not conn:
            return []
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema='ddos' AND table_type='BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            cur.close()
            return tables
        except Exception:
            return []

    def populate_subquery_tables(self):
        tables = self.get_schema_tables()
        if not tables:
            tables = ["experiments"]
        self.subquery_table_combo.blockSignals(True)
        self.subquery_table_combo.clear()
        for table in tables:
            self.subquery_table_combo.addItem(table, table)
        self.subquery_table_combo.blockSignals(False)
        self.populate_subquery_columns()

    def populate_subquery_columns(self):
        table = self.subquery_table_combo.currentData()
        columns = [col[0] for col in get_table_columns(table)] if table else []
        combos = [
            self.subquery_column_combo,
            self.subquery_link_column_combo,
            self.subquery_filter_column_combo,
        ]
        for combo in combos:
            combo.clear()
            for col in columns:
                combo.addItem(col, col)

    def update_subquery_controls(self):
        mode = self.subquery_type.currentData()
        has_filter = mode is not None
        compare_mode = mode in ("ANY", "ALL")
        exists_mode = mode in ("EXISTS", "NOT EXISTS")
        
        self.outer_column_combo.setEnabled(has_filter)
        self.subquery_table_combo.setEnabled(has_filter)
        self.subquery_column_combo.setEnabled(has_filter)
        self.subquery_filter_column_combo.setEnabled(has_filter)
        self.subquery_filter_operator.setEnabled(has_filter)
        self.subquery_filter_value.setEnabled(has_filter)
        
        self.subquery_operator.setEnabled(compare_mode)
        self.subquery_link_column_combo.setEnabled(exists_mode)

    def update_outer_columns(self, columns):
        self.outer_column_combo.clear()
        for col in columns:
            self.outer_column_combo.addItem(COLUMN_LABELS.get(col, col), col)

    def quote_ident(self, name):
        return '"' + str(name).replace('"', '""') + '"'

    def qualify_column(self, table, column):
        return f"ddos.{self.quote_ident(table)}.{self.quote_ident(column)}"

    def format_literal(self, value):
        value = value.strip()
        if not value:
            return "''"
        try:
            if "." in value:
                float(value)
            else:
                int(value)
            return value
        except ValueError:
            return "'" + value.replace("'", "''") + "'"

    def build_subquery_condition(self, table):
        sub_type = self.subquery_type.currentData()
        if not sub_type:
            return None
        
        sub_table = self.subquery_table_combo.currentData()
        sub_column = self.subquery_column_combo.currentData()
        if not sub_table or not sub_column:
            return None
        
        sub_table_sql = f"ddos.{self.quote_ident(sub_table)}"
        filter_col = self.subquery_filter_column_combo.currentData()
        filter_val = self.subquery_filter_value.text().strip()
        where_parts = []
        if filter_col and filter_val:
            filter_op = self.subquery_filter_operator.currentText()
            where_parts.append(
                f"{self.quote_ident(filter_col)} {filter_op} {self.format_literal(filter_val)}"
            )
        
        if sub_type in ("EXISTS", "NOT EXISTS"):
            outer_col = self.outer_column_combo.currentData()
            link_col = self.subquery_link_column_combo.currentData()
            if not (outer_col and link_col):
                return None
            where_parts.insert(
                0,
                f"{self.quote_ident(link_col)} = {self.qualify_column(table, outer_col)}"
            )
            where_sql = " AND ".join(where_parts) if where_parts else "TRUE"
            subquery = f"SELECT 1 FROM {sub_table_sql} WHERE {where_sql}"
            return f"{sub_type} ({subquery})"
        else:
            outer_col = self.outer_column_combo.currentData()
            if not outer_col:
                return None
            where_sql = ""
            if where_parts:
                where_sql = " WHERE " + " AND ".join(where_parts)
            subquery = f"SELECT {self.quote_ident(sub_column)} FROM {sub_table_sql}{where_sql}"
            operator = self.subquery_operator.currentText()
            return f"{self.qualify_column(table, outer_col)} {operator} {sub_type} ({subquery})"

    def load_data(self):
        """Загрузить данные из БД с применением фильтров и всегда актуальной структурой столбцов"""
        table = self.table_selector.currentData()
        if not table:
            table = self.populate_tables()
        attack_type = self.attack_filter.currentData()
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        extra_condition = self.build_subquery_condition(table)
        extra_conditions = [extra_condition] if extra_condition else None
        data = get_data(attack_type, date_from, date_to, table_name=table, extra_conditions=extra_conditions)
        colinfo = get_table_columns(table)
        sql_columns = [col[0] for col in colinfo]
        self.update_outer_columns(sql_columns)
        headers = [COLUMN_LABELS.get(col, col) for col in sql_columns]
        self.table.setColumnCount(len(sql_columns))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(data) if data else 0)
        aux_lookup = {item["id"]: item for item in get_auxiliary_items()}
        for row, record in enumerate(data):
            for col, value in enumerate(record):
                display_value = ""
                if value is not None:
                    if col < len(sql_columns) and sql_columns[col] == "auxiliary_id":
                        info = aux_lookup.get(value)
                        if info:
                            display_value = f"{info['label']} · {info['segment_code']} ({info['criticality']})"
                        else:
                            display_value = str(value)
                    else:
                        display_value = str(value)
                self.table.setItem(row, col, QTableWidgetItem(display_value))
        self.table.resizeColumnsToContents()
        if not data:
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
        
        # Кнопка 1.1: Удалить базу
        btn_drop = QPushButton("Удалить базу")
        btn_drop.clicked.connect(self.on_drop)
        layout.addWidget(btn_drop)
        
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
    
    def on_drop(self):
        """Удалить схему и все созданные объекты"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Удалить схему 'ddos' со всеми таблицами и данными?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        success, msg = drop_schema()
        if success:
            QMessageBox.information(self, "Готово", msg)
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

