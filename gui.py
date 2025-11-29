"""
Графический интерфейс приложения
"""
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QDialog, QFormLayout, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QDateEdit, QGroupBox, QSpinBox, QDoubleSpinBox, QCheckBox, QLabel
)
from PySide6.QtCore import QDate, Qt
from db import create_schema, drop_schema, insert_data, get_data, get_auxiliary_items
from config import ATTACK_TYPES
from alter_dialog import AlterTableDialog, COLUMN_LABELS
from advanced_view_dialog import AdvancedViewDialog
from types_dialog import TypesManagerDialog
from db import get_table_columns, get_connection, get_auxiliary_items, insert_auxiliary_data, generate_test_data, insert_dynamic_data, get_enum_labels, get_composite_type_fields

#sdfdsf
class InputDialog(QDialog):
    """
    Модальное окно для ввода данных эксперимента
    
    Теперь оно ДИНАМИЧЕСКОЕ: само смотрит какие есть колонки в базе
    и создает для них поля ввода.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить данные")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        main_layout = QVBoxLayout()
        
        # Выбор таблицы
        table_layout = QHBoxLayout()
        table_layout.addWidget(QLabel("Таблица:"))
        self.table_combo = QComboBox()
        self.populate_tables()
        self.table_combo.currentTextChanged.connect(self.build_form)
        table_layout.addWidget(self.table_combo)
        main_layout.addLayout(table_layout)
        
        # Форма для полей
        self.form_layout = QFormLayout()
        self.widgets = {} # Словарь для хранения виджетов {col_name: widget}
        main_layout.addLayout(self.form_layout)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)
        
        # Строим форму для первой таблицы
        self.build_form()
    
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

    def populate_tables(self):
        tables = self.get_schema_tables()
        if not tables:
            tables = ["experiments"] # Fallback
        self.table_combo.addItems(tables)
        
    def build_form(self):
        """Перестроить форму в зависимости от выбранной таблицы"""
        # Очистить текущую форму
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)
        self.widgets.clear()
        
        table_name = self.table_combo.currentText()
        if not table_name:
            return

        # Получаем структуру таблицы из БД
        columns_info = get_table_columns(table_name)
        
        if not columns_info:
            # Если колонок нет (или таблица не найдена), ничего не добавляем
            return
        
        for col_name, data_type, is_nullable, default, udt_name in columns_info:
            # Пропускаем ID, так как он автоинкремент (SERIAL)
            if col_name == 'id':
                continue
                
            label = COLUMN_LABELS.get(col_name, col_name)
            widget = None
            
            # 1. ENUM или COMPOSITE (Пользовательские типы)
            if data_type == 'USER-DEFINED': 
                # Пытаемся получить допустимые значения из БД (для ENUM)
                enum_values = get_enum_labels(udt_name)
                
                if enum_values:
                    # Это ENUM
                    widget = QComboBox()
                    widget.addItems(enum_values)
                else:
                    # Проверяем, может это составной тип?
                    comp_fields = get_composite_type_fields(udt_name)
                    if comp_fields:
                        # Это Составной тип! Рисуем под-форму
                        group = QGroupBox(f"{label} ({udt_name})")
                        group_layout = QFormLayout()
                        sub_widgets = {}
                        
                        for field_name, field_type in comp_fields:
                            sub_widget = QLineEdit()
                            sub_widget.setPlaceholderText(field_type)
                            group_layout.addRow(f"{field_name}:", sub_widget)
                            sub_widgets[field_name] = sub_widget
                            
                        group.setLayout(group_layout)
                        # Сохраняем не сам виджет, а словарь виджетов, чтобы потом собрать
                        # Используем специальный класс-обертку или просто пометим
                        widget = group
                        widget.sub_widgets = sub_widgets # Прикрепляем ссылки
                        widget.is_composite = True
                    else:
                        # Если не нашли значений и полей (возможно это не ENUM и не COMPOSITE или ошибка),
                        # проверяем хардкод для attack_type на всякий случай
                        if col_name == 'attack_type':
                            widget = QComboBox()
                            widget.addItems(ATTACK_TYPES)
                        else:
                            # Иначе просто текстовое поле
                            widget = QLineEdit()
            
            # 1.1 Специальное поле Criticality (хоть оно и varchar, но там CHECK constraint)
            elif col_name == 'criticality':
                widget = QComboBox()
                widget.addItems(['LOW', 'MEDIUM', 'HIGH'])
                
            # 2. Foreign Key (Связь с целью)
            elif col_name == 'auxiliary_id':
                widget = QComboBox()
                widget.addItem("Не выбрано", None)
                try:
                    for item in get_auxiliary_items():
                        display = f"{item['label']} · {item['segment_code']} ({item['criticality']})"
                        widget.addItem(display, item["id"])
                except Exception:
                    pass
            
            # 3. Числа (Integer)
            elif data_type in ('integer', 'smallint', 'bigint'):
                widget = QSpinBox()
                widget.setRange(0, 2147483647)
                # Если это packets, ставим дефолт
                if col_name == 'packets':
                    widget.setValue(1000)
                    widget.setRange(1, 2147483647) # CHECK packets > 0
                
            # 4. Дробные (Decimal, Real)
            elif data_type in ('numeric', 'decimal', 'real', 'double precision'):
                widget = QDoubleSpinBox()
                widget.setRange(0.0, 99999999.99)
                widget.setDecimals(2)
                # Если duration
                if col_name == 'duration':
                    widget.setValue(10.0)
                    
            # 5. Дата/Время
            elif 'timestamp' in data_type or 'date' in data_type:
                widget = QDateEdit()
                widget.setDate(QDate.currentDate())
                widget.setCalendarPopup(True)
                
            # 6. Булево
            elif data_type == 'boolean':
                widget = QCheckBox("Да/Нет")
                
            # 7. Текст (все остальное)
            else:
                widget = QLineEdit()
                if col_name == 'name':
                    widget.setPlaceholderText("Например: Тест-1")
                
            if widget:
                self.widgets[col_name] = widget
                self.form_layout.addRow(f"{label}:", widget)
    
    def save(self):
        """Собираем данные из виджетов и сохраняем"""
        table_name = self.table_combo.currentText()
        if not table_name:
            return

        data = {}
        errors = []
        
        for col_name, widget in self.widgets.items():
            val = None
            
            # Обработка составного типа
            if getattr(widget, 'is_composite', False):
                # Собираем значения полей в строку (val1, val2)
                # Важно: если значение содержит запятые или скобки, его надо экранировать в кавычки
                parts = []
                all_empty = True
                for s_name, s_widget in widget.sub_widgets.items():
                    s_val = s_widget.text().strip()
                    if s_val:
                        all_empty = False
                    # Экранирование для композитного типа
                    if ',' in s_val or '(' in s_val or ')' in s_val or '"' in s_val or '\\' in s_val or ' ' in s_val:
                         s_val = '"' + s_val.replace('"', '""') + '"'
                    parts.append(s_val)
                
                if all_empty:
                    val = None
                else:
                    # Формат PostgreSQL: (val1,val2,...)
                    val = "(" + ",".join(parts) + ")"
            
            elif isinstance(widget, QLineEdit):
                text = widget.text().strip()
                if not text:
                    val = None
                else:
                    val = text
            
            elif isinstance(widget, QComboBox):
                if col_name == 'auxiliary_id':
                    val = widget.currentData()
                else:
                    val = widget.currentText()
            
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                val = widget.value()
                
            elif isinstance(widget, QDateEdit):
                val = widget.date().toString("yyyy-MM-dd")
                
            elif isinstance(widget, QCheckBox):
                val = widget.isChecked()
            
            # Проверка обязательных полей (упрощенная)
            if col_name == 'name' and not val:
                 errors.append("Поле 'Название' обязательно")
            
            data[col_name] = val
            
        if errors:
            QMessageBox.warning(self, "Ошибка", "\n".join(errors))
            return

        success, msg = insert_dynamic_data(table_name, data)
        
        if success:
            QMessageBox.information(self, "Успех", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка БД", msg)


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
        
        # Кнопка сброса фильтров
        btn_reset = QPushButton("Сбросить фильтры")
        btn_reset.clicked.connect(self.reset_filters)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_reset)
        
        layout.addLayout(filter_layout)
        layout.addLayout(btn_layout)
        
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

    def reset_filters(self):
        """Сбросить все фильтры и перезагрузить данные."""
        self.attack_filter.setCurrentIndex(0)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_to.setDate(QDate.currentDate())
        self.subquery_type.setCurrentIndex(0)
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
        
        from PySide6.QtWidgets import QHBoxLayout
        
        self.subquery_type = QComboBox()
        self.subquery_type.addItem("Не использовать", None)
        self.subquery_type.addItem("EXISTS (Существует)", "EXISTS")
        self.subquery_type.addItem("NOT EXISTS (Не существует)", "NOT EXISTS")
        self.subquery_type.addItem("ANY (Любой из...)", "ANY")
        self.subquery_type.addItem("ALL (Каждый из...)", "ALL")
        form.addRow("Тип фильтра:", self.subquery_type)
        
        self.outer_column_combo = QComboBox()
        form.addRow("Искать по полю:", self.outer_column_combo)
        
        self.subquery_operator = QComboBox()
        self.subquery_operator.addItems(["=", "<>", ">", ">=", "<", "<="])
        form.addRow("Оператор сравнения:", self.subquery_operator)
        
        self.subquery_table_combo = QComboBox()
        self.subquery_table_combo.currentIndexChanged.connect(self.populate_subquery_columns)
        form.addRow("Где искать (Таблица):", self.subquery_table_combo)
        
        self.subquery_column_combo = QComboBox()
        form.addRow("Поле подзапроса:", self.subquery_column_combo)
        
        self.subquery_link_column_combo = QComboBox()
        form.addRow("Связующее поле (ID):", self.subquery_link_column_combo)
        
        self.subquery_filter_column_combo = QComboBox()
        form.addRow("Условие (Поле):", self.subquery_filter_column_combo)
        
        self.subquery_filter_operator = QComboBox()
        self.subquery_filter_operator.addItems(["=", "<>", ">", ">=", "<", "<="])
        form.addRow("Условие (Оператор):", self.subquery_filter_operator)
        
        self.subquery_filter_value = QLineEdit()
        form.addRow("Условие (Значение):", self.subquery_filter_value)
        
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
        
        # Общая видимость блока (кроме селектора типа)
        self.outer_column_combo.setVisible(has_filter and compare_mode)
        self.subquery_table_combo.setVisible(has_filter)
        self.subquery_column_combo.setVisible(has_filter and compare_mode)
        self.subquery_filter_column_combo.setVisible(has_filter)
        self.subquery_filter_operator.setVisible(has_filter)
        self.subquery_filter_value.setVisible(has_filter)
        
        self.subquery_operator.setVisible(compare_mode)
        self.subquery_link_column_combo.setVisible(exists_mode)
        
        # Обновление лейблов (скрываем строки формы по индексам добавления)
        layout = self.subquery_type.parent().layout()
        if layout:
            # 0: Type (всегда виден)
            # 1: Outer Column (Искать по полю) -> ANY/ALL
            # 2: Operator (Оператор сравнения) -> ANY/ALL
            # 3: Table (Где искать) -> ВСЕГДА при наличии типа
            # 4: Sub Column (Поле подзапроса) -> ANY/ALL
            # 5: Link Column (Связующее поле) -> EXISTS
            # 6: Filter Column (Условие Поле) -> ВСЕГДА при наличии типа
            # 7: Filter Op (Условие Оператор) -> ВСЕГДА при наличии типа
            # 8: Filter Val (Условие Значение) -> ВСЕГДА при наличии типа
            
            # Сначала скрываем всё кроме типа (0)
            for i in range(1, layout.rowCount()):
                layout.setRowVisible(i, False)
            
            if has_filter:
                layout.setRowVisible(3, True) # Table
                layout.setRowVisible(6, True) # Filter Col
                layout.setRowVisible(7, True) # Filter Op
                layout.setRowVisible(8, True) # Filter Val
                
                if compare_mode:
                    layout.setRowVisible(1, True) # Outer Col
                    layout.setRowVisible(2, True) # Op
                    layout.setRowVisible(4, True) # Sub Col
                
                if exists_mode:
                    layout.setRowVisible(1, True) # Outer Col (нужен для связи)
                    layout.setRowVisible(5, True) # Link Col

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

        # Кнопка 6: Управление типами
        btn_types = QPushButton("Управление типами")
        btn_types.clicked.connect(self.on_types)
        layout.addWidget(btn_types)
    
        # Кнопка 7: Генерация тестовых данных
        btn_gen = QPushButton("Генерация тестовых данных")
        btn_gen.clicked.connect(self.on_generate)
        layout.addWidget(btn_gen)
    
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

    def on_types(self):
        """Обработчик нажатия кнопки 'Управление типами'"""
        dialog = TypesManagerDialog(self)
        dialog.exec()

    def on_generate(self):
        """Обработчик нажатия кнопки 'Генерация тестовых данных'"""
        reply = QMessageBox.question(
            self, 
            "Подтверждение", 
            "Сгенерировать 15 случайных записей в таблице экспериментов?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success, msg = generate_test_data()
            if success:
                QMessageBox.information(self, "Успех", msg)
            else:
                QMessageBox.critical(self, "Ошибка", msg)
