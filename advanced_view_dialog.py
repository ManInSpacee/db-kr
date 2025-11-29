
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QLabel, QCheckBox, QTabWidget, QWidget, QGroupBox,
    QScrollArea
)
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QDateEdit
from db import execute_custom_query, get_table_columns, get_connection


def quote_ident(name: str) -> str:
    """Простое экранирование идентификаторов для SQL."""
    return '"' + name.replace('"', '""') + '"'


class AdvancedViewDialog(QDialog):
    """Расширенное окно для работы с данными"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Мастер создания запросов (Advanced View)")
        self.setModal(True)
        self.setMinimumSize(1000, 750)
        
        layout = QVBoxLayout()
        
        # Вкладки для разных функций
        tabs = QTabWidget()
        
        # Вкладка 1: Базовый SELECT
        tab_select = QWidget()
        tabs.addTab(tab_select, "Сборка данных (SELECT)")
        self.setup_select_tab(tab_select)
        
        # Вкладка 2: Поиск по тексту
        tab_search = QWidget()
        tabs.addTab(tab_search, "Поиск текста")
        self.setup_search_tab(tab_search)
        
        # Вкладка 3: Функции строк
        tab_strings = QWidget()
        tabs.addTab(tab_strings, "Работа со строками")
        self.setup_strings_tab(tab_strings)
        
        # Вкладка 4: JOIN
        tab_join = QWidget()
        tabs.addTab(tab_join, "Связи таблиц (JOIN)")
        self.setup_join_tab(tab_join)
        
        # Вкладка 5: Условия и NULL (CASE, COALESCE)
        tab_logic = QWidget()
        tabs.addTab(tab_logic, "Логика и Условия")
        self.setup_logic_tab(tab_logic)
        
        layout.addWidget(tabs)
        
        # Таблица для результатов
        layout.addWidget(QLabel("<b>Результат выполнения:</b>"))
        self.table = QTableWidget()
        layout.addWidget(self.table)
        
        # Кнопки
        buttons = QHBoxLayout()
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(btn_close)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
    
    def setup_select_tab(self, tab):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        scroll.setWidget(content_widget)
        
        # Главный Layout вкладки
        tab_layout = QVBoxLayout()
        tab_layout.addWidget(QLabel("<i>Соберите свою таблицу, выбрав источник данных, колонки и условия фильтрации.</i>"))
        tab_layout.addWidget(scroll)
        tab.setLayout(tab_layout)

        # 1. Источник данных
        group_source = QGroupBox("1. Источник данных")
        src_layout = QHBoxLayout()
        src_layout.addWidget(QLabel("Выберите таблицу:"))
        self.select_table_combo = QComboBox()
        self.populate_table_combo(self.select_table_combo)
        src_layout.addWidget(self.select_table_combo)
        group_source.setLayout(src_layout)
        layout.addWidget(group_source)
        
        # 2. Выбор столбцов
        group_cols = QGroupBox("2. Что показывать (Столбцы)")
        cols_layout = QVBoxLayout()
        cols_layout.addWidget(QLabel("Введите имена столбцов через запятую (например: name, duration):"))
        self.columns_text = QTextEdit()
        self.columns_text.setPlaceholderText("По умолчанию: * (все столбцы)")
        self.columns_text.setMaximumHeight(50)
        cols_layout.addWidget(self.columns_text)
        group_cols.setLayout(cols_layout)
        layout.addWidget(group_cols)
        
        # 3. Фильтрация (WHERE)
        group_where = QGroupBox("3. Фильтрация строк (WHERE)")
        where_layout = QHBoxLayout()
        
        self.where_col = QComboBox()
        self.populate_column_combo(self.where_col, self.select_table_combo.currentData())
        
        self.where_op = QComboBox()
        self.where_op.addItems(["=", ">", ">=", "<", "<=", "<>", "LIKE"])
        
        self.where_val = QLineEdit()
        self.where_val.setPlaceholderText("Значение (например: 100)")
        
        where_layout.addWidget(QLabel("Если поле:"))
        where_layout.addWidget(self.where_col)
        where_layout.addWidget(QLabel("Оператор:"))
        where_layout.addWidget(self.where_op)
        where_layout.addWidget(QLabel("Значение:"))
        where_layout.addWidget(self.where_val)
        
        group_where.setLayout(where_layout)
        layout.addWidget(group_where)

        # Подключение обновления колонок
        self.select_table_combo.currentIndexChanged.connect(
            lambda: self.populate_column_combo(self.where_col, self.select_table_combo.currentData())
        )
        
        # 4. Сортировка (ORDER BY)
        group_order = QGroupBox("4. Сортировка (ORDER BY)")
        order_layout = QHBoxLayout()
        
        self.order_by_combo = QComboBox()
        # include_empty=True для сортировки
        self.populate_column_combo(self.order_by_combo, self.select_table_combo.currentData(), include_empty=True)
        
        self.order_direction = QComboBox()
        self.order_direction.addItems(["По возрастанию (ASC)", "По убыванию (DESC)"])
        
        order_layout.addWidget(QLabel("Сортировать по:"))
        order_layout.addWidget(self.order_by_combo)
        order_layout.addWidget(self.order_direction)
        
        group_order.setLayout(order_layout)
        layout.addWidget(group_order)

        self.select_table_combo.currentIndexChanged.connect(
            lambda: self.populate_column_combo(self.order_by_combo, self.select_table_combo.currentData(), include_empty=True)
        )
        
        # 5. Группировка и Агрегация
        group_agg = QGroupBox("5. Группировка и Статистика (GROUP BY / HAVING)")
        agg_layout = QFormLayout()
        
        self.group_by_combo = QComboBox()
        # include_empty=True для группировки (пункт будет "Не выбрано")
        self.populate_column_combo(self.group_by_combo, self.select_table_combo.currentData(), include_empty=True)
        agg_layout.addRow("Сгруппировать по полю:", self.group_by_combo)
        
        # HAVING
        having_box = QHBoxLayout()
        self.having_agg = QComboBox()
        self.having_agg.addItems(["COUNT(*)", "SUM(packets)", "AVG(packets)", "MIN(packets)", "MAX(packets)"])
        self.having_op = QComboBox()
        self.having_op.addItems([">", ">=", "<", "<=", "=", "<>"])
        self.having_val = QLineEdit()
        self.having_val.setPlaceholderText("Например: 10")
        
        having_box.addWidget(self.having_agg)
        having_box.addWidget(self.having_op)
        having_box.addWidget(self.having_val)
        
        agg_layout.addRow("Условие для группы (HAVING):", having_box)
        
        group_agg.setLayout(agg_layout)
        layout.addWidget(group_agg)

        self.select_table_combo.currentIndexChanged.connect(
            lambda: self.populate_column_combo(self.group_by_combo, self.select_table_combo.currentData(), include_empty=True)
        )
        
        btn_execute = QPushButton("ВЫПОЛНИТЬ ЗАПРОС")
        btn_execute.setStyleSheet("font-weight: bold; padding: 5px;")
        btn_execute.clicked.connect(self.execute_select)
        layout.addWidget(btn_execute)
        
        layout.addStretch()
    
    def setup_search_tab(self, tab):
        """Настройка вкладки поиска"""
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        layout.addWidget(QLabel("<i>Поиск текстовых данных с использованием шаблонов и регулярных выражений.</i>"))
        
        form_group = QGroupBox("Параметры поиска")
        form = QFormLayout()
        
        self.search_table_combo = QComboBox()
        self.populate_table_combo(self.search_table_combo)
        form.addRow("Таблица:", self.search_table_combo)
        
        self.search_column = QComboBox()
        self.populate_column_combo(self.search_column, self.search_table_combo.currentData())
        self.search_table_combo.currentTextChanged.connect(
            lambda _: self.populate_column_combo(self.search_column, self.search_table_combo.currentData())
        )
        form.addRow("Поле для поиска:", self.search_column)
        
        self.search_type = QComboBox()
        self.search_type.addItems([
            "LIKE (Простой шаблон %)",
            "ILIKE (Простой шаблон, без регистра)",
            "~ (POSIX RegEx: Регулярное выражение)",
            "~* (POSIX RegEx: Без учета регистра)",
            "!~ (POSIX: НЕ соответствует)",
            "!~* (POSIX: НЕ соответствует, без регистра)",
            "SIMILAR TO (SQL Стандарт)",
            "NOT SIMILAR TO (SQL Стандарт: НЕ соответствует)"
        ])
        form.addRow("Метод поиска:", self.search_type)
        
        self.search_pattern = QLineEdit()
        self.search_pattern.setPlaceholderText("Например: ^Test.*")
        form.addRow("Текст или шаблон:", self.search_pattern)
        
        form_group.setLayout(form)
        layout.addWidget(form_group)
        
        help_group = QGroupBox("Подсказка по шаблонам")
        help_layout = QVBoxLayout()
        help_label = QLabel(
        )
        help_layout.addWidget(help_label)
        help_group.setLayout(help_layout)
        layout.addWidget(help_group)
        
        btn_search = QPushButton("Найти")
        btn_search.clicked.connect(self.execute_search)
        layout.addWidget(btn_search)
        
        layout.addStretch()
    # LOL
    def setup_strings_tab(self, tab):
        """Настройка вкладки функций работы со строками"""
        layout = QVBoxLayout()
        tab.setLayout(layout)

        layout.addWidget(QLabel("<i>Преобразование текста прямо в базе данных.</i>"))

        group = QGroupBox("Настройка операции")
        form = QFormLayout()

        self.strings_table_combo = QComboBox()
        self.populate_table_combo(self.strings_table_combo)
        form.addRow("Таблица:", self.strings_table_combo)
        
        self.string_column = QComboBox()
        self.populate_column_combo(self.string_column, self.strings_table_combo.currentData())
        self.strings_table_combo.currentTextChanged.connect(
            lambda _: self.populate_column_combo(self.string_column, self.strings_table_combo.currentData())
        )
        form.addRow("Исходный столбец:", self.string_column)
        
        self.string_func = QComboBox()
        self.string_func.addItems([
            "UPPER (Сделать ЗАГЛАВНЫМИ)",
            "LOWER (сделать строчными)",
            "TRIM (Удалить пробелы по краям)",
            "SUBSTRING (Вырезать часть текста)",
            "CONCAT (Объединить с другим текстом)",
            "LPAD (Дополнить символами слева)",
            "RPAD (Дополнить символами справа)"
        ])
        self.string_func.currentTextChanged.connect(self.update_string_params)
        form.addRow("Функция:", self.string_func)
        
        self.string_param1 = QLineEdit()
        self.string_param1.setPlaceholderText("Параметр 1")
        form.addRow("Параметр 1:", self.string_param1)
        
        self.string_param2 = QLineEdit()
        self.string_param2.setPlaceholderText("Параметр 2")
        form.addRow("Параметр 2:", self.string_param2)
        
        group.setLayout(form)
        layout.addWidget(group)
        
        btn_execute = QPushButton("Выполнить преобразование")
        btn_execute.clicked.connect(self.execute_strings)
        layout.addWidget(btn_execute)
        
        layout.addStretch()
    
    def setup_join_tab(self, tab):
        """Настройка вкладки JOIN"""
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        layout.addWidget(QLabel("<i>Объединение данных из двух таблиц по общему полю.</i>"))
        
        group = QGroupBox("Параметры соединения")
        form = QFormLayout()
        
        self.join_type = QComboBox()
        self.join_type.addItems([
            "INNER JOIN (Только совпадения)", 
            "LEFT JOIN (Все из левой + совпадения)", 
            "RIGHT JOIN (Все из правой + совпадения)", 
            "FULL JOIN (Все записи из обеих)"
        ])
        form.addRow("Тип связи:", self.join_type)
        
        # Таблицы
        tables = self.get_schema_tables()
        if not tables:
            tables = ["experiments"]
        
        self.join_table1 = QComboBox()
        for table in tables:
            self.join_table1.addItem(table, table)
        form.addRow("Левая таблица:", self.join_table1)
        
        self.join_table2 = QComboBox()
        for table in tables:
            self.join_table2.addItem(table, table)
        form.addRow("Правая таблица:", self.join_table2)
        
        # Поля
        self.join_field1 = QComboBox()
        self.join_field2 = QComboBox()
        form.addRow("Поле связи (из левой):", self.join_field1)
        form.addRow("Поле связи (из правой):", self.join_field2)
        
        self.join_table1.currentTextChanged.connect(lambda _: self.populate_join_fields(self.join_table1, self.join_field1))
        self.join_table2.currentTextChanged.connect(lambda _: self.populate_join_fields(self.join_table2, self.join_field2))
        self.populate_join_fields(self.join_table1, self.join_field1)
        self.populate_join_fields(self.join_table2, self.join_field2)
        
        self.join_columns = QTextEdit()
        self.join_columns.setPlaceholderText("По умолчанию: * (Все поля)")
        self.join_columns.setMaximumHeight(50)
        form.addRow("Какие поля показать:", self.join_columns)
        
        group.setLayout(form)
        layout.addWidget(group)
        
        btn_execute = QPushButton("Объединить таблицы (JOIN)")
        btn_execute.clicked.connect(self.execute_join)
        layout.addWidget(btn_execute)
        
        layout.addStretch()

    def setup_logic_tab(self, tab):
        """Настройка вкладки Условия и NULL"""
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # Выбор таблицы
        src_layout = QHBoxLayout()
        src_layout.addWidget(QLabel("Таблица:"))
        self.logic_table_combo = QComboBox()
        self.populate_table_combo(self.logic_table_combo)
        src_layout.addWidget(self.logic_table_combo)
        layout.addLayout(src_layout)
        
        # Раздел CASE
        case_group = QGroupBox("1. Конструктор условий (CASE)")
        case_layout = QVBoxLayout()
        case_layout.addWidget(QLabel("<i>Если выполняется условие WHEN, то вернуть значение THEN.</i>"))
        
        # Таблица условий
        self.case_table = QTableWidget(3, 2)
        self.case_table.setHorizontalHeaderLabels(["Если (Условие)", "То (Результат)"])
        self.case_table.horizontalHeader().setStretchLastSection(True)
        case_layout.addWidget(self.case_table)
        
        # ELSE
        form_else = QFormLayout()
        self.case_else = QLineEdit()
        self.case_else.setPlaceholderText("Иначе NULL")
        form_else.addRow("Иначе (ELSE):", self.case_else)
        case_layout.addLayout(form_else)
        
        btn_case = QPushButton("Выполнить CASE")
        btn_case.clicked.connect(self.execute_case)
        case_layout.addWidget(btn_case)
        
        case_group.setLayout(case_layout)
        layout.addWidget(case_group)
        
        # Раздел NULL функций
        null_group = QGroupBox("2. Обработка пустых значений (NULL)")
        null_layout = QFormLayout()
        
        self.null_func = QComboBox()
        self.null_func.addItems(["COALESCE (Заменить NULL на...)", "NULLIF (Вернуть NULL если равно...)"])
        null_layout.addRow("Функция:", self.null_func)
        
        self.null_arg1 = QLineEdit()
        self.null_arg1.setPlaceholderText("Поле или значение")
        null_layout.addRow("Аргумент 1:", self.null_arg1)
        
        self.null_arg2 = QLineEdit()
        self.null_arg2.setPlaceholderText("Значение замены / Сравнения")
        null_layout.addRow("Аргумент 2:", self.null_arg2)
        
        btn_null = QPushButton("Выполнить")
        btn_null.clicked.connect(self.execute_null_func)
        null_layout.addWidget(btn_null)
        
        null_group.setLayout(null_layout)
        layout.addWidget(null_group)
        
        layout.addStretch()
    
    def get_schema_tables(self):
        """Получить список таблиц схемы ddos."""
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
    
    def populate_table_combo(self, combo):
        tables = self.get_schema_tables()
        if not tables:
            tables = ["experiments"]
        combo.clear()
        for table in tables:
            combo.addItem(table, table)
        combo.setCurrentIndex(0)

    def populate_column_combo(self, combo, table_name, include_empty=False):
        combo.clear()
        if include_empty:
            combo.addItem("Не выбрано", "")
        if not table_name:
            return
        columns = [col[0] for col in get_table_columns(table_name)]
        for col in columns:
            combo.addItem(col, col)

    def populate_join_fields(self, table_combo, fields_combo):
        """Обновить список колонок для выбранной таблицы."""
        table_name = table_combo.currentData()
        fields_combo.clear()
        if not table_name:
            return
        columns = [col[0] for col in get_table_columns(table_name)]
        for col in columns:
            fields_combo.addItem(col, col)

    def update_string_params(self):
        """Обновить параметры для функций строк"""
        func = self.string_func.currentText()
        if "SUBSTRING" in func:
            self.string_param1.setPlaceholderText("Начало (например: 1)")
            self.string_param2.setPlaceholderText("Длина (например: 5)")
        elif "LPAD" in func or "RPAD" in func:
            self.string_param1.setPlaceholderText("Длина")
            self.string_param2.setPlaceholderText("Символ заполнения")
        elif "CONCAT" in func:
            self.string_param1.setPlaceholderText("Второй столбец или текст")
            self.string_param2.setPlaceholderText("Третий столбец или текст (опционально)")
        else:
            self.string_param1.setPlaceholderText("Параметр 1")
            self.string_param2.setPlaceholderText("Параметр 2")
    
    def build_select_query(self):
        """Построить SELECT запрос"""
        # Столбцы
        columns = self.columns_text.toPlainText().strip()
        if not columns:
            columns = "*"
        
        table = self.select_table_combo.currentData() or "experiments"
        query = f"SELECT {columns} FROM ddos.{quote_ident(table)}"
        
        # WHERE
        where_col = self.where_col.currentData()
        where_val = self.where_val.text().strip()
        if where_col and where_val:
            op = self.where_op.currentText()
            # Форматирование значения (число или строка)
            try:
                float(where_val)
            except ValueError:
                where_val = f"'{where_val}'"
            query += f" WHERE {quote_ident(where_col)} {op} {where_val}"
        
        # GROUP BY
        group_by = self.group_by_combo.currentData()
        # Проверяем, не выбрано ли "Не группировать" (пустой текст или спец значение)
        if group_by:
            query += f" GROUP BY {quote_ident(group_by)}"
        
        # HAVING
        having_val = self.having_val.text().strip()
        if having_val:
            agg = self.having_agg.currentText()
            op = self.having_op.currentText()
            # Простая защита от инъекций для числовых значений
            if not having_val.replace('.', '', 1).isdigit():
                having_val = f"'{having_val}'"
            query += f" HAVING {agg} {op} {having_val}"
        
        # ORDER BY
        order_col = self.order_by_combo.currentData()
        if order_col:
            order_dir = "DESC" if "DESC" in self.order_direction.currentText() else "ASC"
            query += f" ORDER BY {quote_ident(order_col)} {order_dir}"
        
        return query
    
    def execute_select(self):
        """Выполнить SELECT запрос"""
        query = self.build_select_query()
        success, data, columns = execute_custom_query(query)
        
        if success:
            self.display_results(data, columns if columns else [])
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка выполнения запроса:\n{data}")
    
    def execute_search(self):
        """Выполнить поиск по тексту"""
        column = self.search_column.currentData()
        pattern = self.search_pattern.text().strip()
        search_type_text = self.search_type.currentText()
        
        if not pattern:
            QMessageBox.warning(self, "Ошибка", "Введите шаблон поиска")
            return
        
        # Определяем оператор из дружелюбного текста
        operator = "LIKE" # Default
        if "LIKE" in search_type_text and "ILIKE" not in search_type_text: operator = "LIKE"
        elif "ILIKE" in search_type_text: operator = "ILIKE"
        elif "~" in search_type_text and "POSIX" in search_type_text:
            if "!~*" in search_type_text: operator = "!~*"
            elif "!~" in search_type_text: operator = "!~"
            elif "~*" in search_type_text: operator = "~*"
            else: operator = "~"
        elif "SIMILAR TO" in search_type_text:
            if "NOT" in search_type_text:
                operator = "NOT SIMILAR TO"
            else:
                operator = "SIMILAR TO"

        # Форматируем шаблон
        pattern_sql = f"'{pattern}'"
        
        table = self.search_table_combo.currentData() or "experiments"
        
        # Для LIKE/ILIKE иногда нужно кастить в text
        col_expr = f"({quote_ident(column)}::text)"
        
        query = f"SELECT * FROM ddos.{quote_ident(table)} WHERE {col_expr} {operator} {pattern_sql}"
        success, data, columns = execute_custom_query(query)
        
        if success:
            self.display_results(data, columns if columns else [])
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка поиска:\n{data}")
    
    def execute_strings(self):
        """Выполнить функции работы со строками"""
        column = self.string_column.currentData()
        col_sql = quote_ident(column) if column else column
        func_text = self.string_func.currentText()
        param1 = self.string_param1.text().strip()
        param2 = self.string_param2.text().strip()
        
        # Строим выражение функции
        # Принудительно кастим к тексту для строковых функций
        col_sql = f"{quote_ident(column)}::text" if column else column
        
        expr = column
        
        if "UPPER" in func_text:
            expr = f"UPPER({col_sql})"
        elif "LOWER" in func_text:
            expr = f"LOWER({col_sql})"
        elif "SUBSTRING" in func_text:
            if not param1 or not param2:
                QMessageBox.warning(self, "Ошибка", "Укажите начало и длину")
                return
            expr = f"SUBSTRING({col_sql} FROM {param1} FOR {param2})"
        elif "TRIM" in func_text:
            expr = f"TRIM({col_sql})"
        elif "LPAD" in func_text:
            if not param1:
                QMessageBox.warning(self, "Ошибка", "Укажите длину")
                return
            pad_char = f"'{param2}'" if param2 else "' '"
            expr = f"LPAD({col_sql}::text, {param1}, {pad_char})"
        elif "RPAD" in func_text:
            if not param1:
                QMessageBox.warning(self, "Ошибка", "Укажите длину")
                return
            pad_char = f"'{param2}'" if param2 else "' '"
            expr = f"RPAD({col_sql}::text, {param1}, {pad_char})"
        elif "CONCAT" in func_text:
            parts = [col_sql]
            if param1: parts.append(f"'{param1}'") # Предполагаем текст
            if param2: parts.append(f"'{param2}'")
            expr = f"CONCAT({', '.join(parts)})"
        
        table = self.strings_table_combo.currentData() or "experiments"
        query = f"SELECT {quote_ident(column)}, {expr} AS result FROM ddos.{quote_ident(table)}"
        success, data, columns = execute_custom_query(query)
        
        if success:
            self.display_results(data, columns if columns else [])
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка выполнения:\n{data}")
    
    def execute_join(self):
        """Выполнить JOIN"""
        # Извлекаем тип JOIN из текста (например "INNER JOIN (Только...)")
        join_type_full = self.join_type.currentText()
        join_type = join_type_full.split(' ')[0] + " JOIN" # Берём первое слово (INNER/LEFT...) + JOIN
        if "FULL" in join_type_full: join_type = "FULL JOIN"

        table1 = self.join_table1.currentData()
        table2 = self.join_table2.currentData()
        field1 = self.join_field1.currentData()
        field2 = self.join_field2.currentData()
        columns = self.join_columns.toPlainText().strip()
        
        if not table1 or not table2:
            QMessageBox.warning(self, "Ошибка", "Укажите обе таблицы")
            return
        
        if not field1 or not field2:
            QMessageBox.warning(self, "Ошибка", "Выберите поля для связывания")
            return
        
        if not columns:
            columns = "*"
        
        t1_sql = f"ddos.{quote_ident(table1)}"
        t2_sql = f"ddos.{quote_ident(table2)}"
        on_condition = f"t1.{quote_ident(field1)} = t2.{quote_ident(field2)}"
        query = f"SELECT {columns} FROM {t1_sql} t1 {join_type} {t2_sql} t2 ON {on_condition}"
        success, data, cols = execute_custom_query(query)
        
        if success:
            self.display_results(data, cols if cols else [])
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка JOIN:\n{data}")
            
    def execute_case(self):
        """Выполнить запрос с CASE"""
        table = self.logic_table_combo.currentData()
        
        cases = []
        for i in range(self.case_table.rowCount()):
            w_item = self.case_table.item(i, 0)
            t_item = self.case_table.item(i, 1)
            if w_item and t_item and w_item.text().strip():
                when_expr = w_item.text().strip()
                then_expr = t_item.text().strip()
                cases.append(f"WHEN {when_expr} THEN {then_expr}")
        
        if not cases:
            QMessageBox.warning(self, "Ошибка", "Заполните хотя бы одно условие")
            return
            
        else_val = self.case_else.text().strip()
        else_part = f" ELSE {else_val}" if else_val else ""
        
        case_sql = "CASE " + " ".join(cases) + else_part + " END"
        
        query = f"SELECT *, {case_sql} AS case_result FROM ddos.{quote_ident(table)}"
        success, data, cols = execute_custom_query(query)
        
        if success:
            self.display_results(data, cols)
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка CASE:\n{data}")

    def execute_null_func(self):
        """Выполнить COALESCE или NULLIF"""
        func_text = self.null_func.currentText()
        arg1 = self.null_arg1.text().strip()
        arg2 = self.null_arg2.text().strip()
        table = self.logic_table_combo.currentData()
        
        if not arg1:
            QMessageBox.warning(self, "Ошибка", "Укажите первый аргумент")
            return
            
        if "COALESCE" in func_text:
            # Для COALESCE второй аргумент может содержать несколько значений через запятую
            # Если аргумент 2 пуст, это ошибка (минимум 2 аргумента обычно, хотя 1 тоже работает в pg)
            args = arg1
            if arg2:
                args += ", " + arg2
            expr = f"COALESCE({args})"
        else: # NULLIF
            if not arg2:
                 QMessageBox.warning(self, "Ошибка", "Для NULLIF нужны 2 аргумента")
                 return
            expr = f"NULLIF({arg1}, {arg2})"
            
        query = f"SELECT *, {expr} AS func_result FROM ddos.{quote_ident(table)}"
        success, data, cols = execute_custom_query(query)
        
        if success:
            self.display_results(data, cols)
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка выполнения:\n{data}")
    
    def display_results(self, data, columns):
        """Отобразить результаты в таблице"""
        if not data:
            self.table.setRowCount(0)
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(["Нет данных"])
            return
        
        # Определяем количество столбцов
        if columns:
            num_cols = len(columns)
            headers = columns
        else:
            num_cols = len(data[0]) if data else 1
            headers = [f"Столбец {i+1}" for i in range(num_cols)]
        
        self.table.setColumnCount(num_cols)
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(data))
        
        # Заполняем таблицу
        for row, record in enumerate(data):
            for col, value in enumerate(record):
                self.table.setItem(row, col, QTableWidgetItem(str(value) if value is not None else ""))
        
        self.table.resizeColumnsToContents()
