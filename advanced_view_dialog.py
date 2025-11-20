"""
Расширенное окно для работы с SELECT
Включает: WHERE, ORDER BY, GROUP BY, HAVING, выбор столбцов,
поиск по тексту, функции работы со строками, JOIN
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QLabel, QCheckBox, QTabWidget, QWidget, QGroupBox
)
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QDateEdit
from db import execute_custom_query, get_table_columns, get_connection


def quote_ident(name: str) -> str:
    """Простое экранирование идентификаторов для SQL."""
    return '"' + name.replace('"', '""') + '"'


class AdvancedViewDialog(QDialog):
    """Расширенное окно для работы с данными"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Расширенный просмотр данных")
        self.setModal(True)
        self.setMinimumSize(1000, 700)
        
        layout = QVBoxLayout()
        
        # Вкладки для разных функций
        tabs = QTabWidget()
        
        # Вкладка 1: Базовый SELECT
        tab_select = QWidget()
        tabs.addTab(tab_select, "SELECT")
        self.setup_select_tab(tab_select)
        
        # Вкладка 2: Поиск по тексту
        tab_search = QWidget()
        tabs.addTab(tab_search, "Поиск")
        self.setup_search_tab(tab_search)
        
        # Вкладка 3: Функции строк
        tab_strings = QWidget()
        tabs.addTab(tab_strings, "Строки")
        self.setup_strings_tab(tab_strings)
        
        # Вкладка 4: JOIN
        tab_join = QWidget()
        tabs.addTab(tab_join, "JOIN")
        self.setup_join_tab(tab_join)
        
        layout.addWidget(tabs)
        
        # Таблица для результатов
        layout.addWidget(QLabel("Результаты:"))
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
        """Настройка вкладки SELECT"""
        layout = QVBoxLayout()
        tab.setLayout(layout)

        # Выбор таблицы
        self.select_table_combo = QComboBox()
        self.populate_table_combo(self.select_table_combo)
        layout.addWidget(QLabel("Таблица:"))
        layout.addWidget(self.select_table_combo)
        
        # Выбор столбцов
        group_cols = QGroupBox("Выбор столбцов")
        cols_layout = QVBoxLayout()
        self.columns_text = QTextEdit()
        self.columns_text.setPlaceholderText("id, name, attack_type, packets, duration\nИли оставьте пустым для всех (*)")
        self.columns_text.setMaximumHeight(60)
        cols_layout.addWidget(self.columns_text)
        group_cols.setLayout(cols_layout)
        layout.addWidget(group_cols)
        
        # WHERE
        group_where = QGroupBox("WHERE (условие фильтрации)")
        where_layout = QVBoxLayout()
        self.where_text = QLineEdit()
        self.where_text.setPlaceholderText("packets > 1000 AND duration < 10")
        where_layout.addWidget(self.where_text)
        group_where.setLayout(where_layout)
        layout.addWidget(group_where)
        
        # ORDER BY
        group_order = QGroupBox("ORDER BY (сортировка)")
        order_layout = QFormLayout()
        self.order_by_text = QLineEdit()
        self.order_by_text.setPlaceholderText("packets DESC")
        self.order_by_text.setText("created_at DESC")
        order_layout.addRow("Сортировка:", self.order_by_text)
        group_order.setLayout(order_layout)
        layout.addWidget(group_order)
        
        # GROUP BY и HAVING
        group_group = QGroupBox("GROUP BY и HAVING")
        group_layout = QFormLayout()
        self.group_by_text = QLineEdit()
        self.group_by_text.setPlaceholderText("attack_type")
        group_layout.addRow("GROUP BY:", self.group_by_text)
        self.having_text = QLineEdit()
        self.having_text.setPlaceholderText("COUNT(*) > 5")
        group_layout.addRow("HAVING:", self.having_text)
        group_group.setLayout(group_layout)
        layout.addWidget(group_group)
        
        # Агрегатные функции
        group_agg = QGroupBox("Агрегатные функции")
        agg_layout = QFormLayout()
        self.agg_func = QComboBox()
        self.agg_func.addItems(["", "COUNT(*)", "SUM(packets)", "AVG(packets)", "MAX(packets)", "MIN(packets)"])
        agg_layout.addRow("Функция:", self.agg_func)
        group_agg.setLayout(agg_layout)
        layout.addWidget(group_agg)
        
        btn_execute = QPushButton("Выполнить запрос")
        btn_execute.clicked.connect(self.execute_select)
        layout.addWidget(btn_execute)
        
        layout.addStretch()
    
    def setup_search_tab(self, tab):
        """Настройка вкладки поиска"""
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        layout.addWidget(QLabel("Таблица:"))
        self.search_table_combo = QComboBox()
        self.populate_table_combo(self.search_table_combo)
        layout.addWidget(self.search_table_combo)
        
        form = QFormLayout()
        
        self.search_column = QComboBox()
        self.populate_column_combo(self.search_column, self.search_table_combo.currentData())
        self.search_table_combo.currentTextChanged.connect(
            lambda _: self.populate_column_combo(self.search_column, self.search_table_combo.currentData())
        )
        form.addRow("Столбец:", self.search_column)
        
        self.search_pattern = QLineEdit()
        self.search_pattern.setPlaceholderText("Введите шаблон поиска")
        form.addRow("Шаблон:", self.search_pattern)
        
        self.search_type = QComboBox()
        self.search_type.addItems([
            "LIKE",
            "ILIKE (без учета регистра)",
            "~ (POSIX регулярное выражение)",
            "~* (POSIX без учета регистра)",
            "!~ (не соответствует POSIX)",
            "!~* (не соответствует POSIX, без регистра)"
        ])
        form.addRow("Тип поиска:", self.search_type)
        
        layout.addLayout(form)
        
        layout.addWidget(QLabel("Примеры:\nLIKE: 'test%' - начинается с test\n~: '^[A-Z]' - начинается с заглавной"))
        
        btn_search = QPushButton("Выполнить поиск")
        btn_search.clicked.connect(self.execute_search)
        layout.addWidget(btn_search)
        
        layout.addStretch()
    
    def setup_strings_tab(self, tab):
        """Настройка вкладки функций работы со строками"""
        layout = QVBoxLayout()
        tab.setLayout(layout)

        layout.addWidget(QLabel("Таблица:"))
        self.strings_table_combo = QComboBox()
        self.populate_table_combo(self.strings_table_combo)
        layout.addWidget(self.strings_table_combo)
        
        form = QFormLayout()
        
        self.string_column = QComboBox()
        self.populate_column_combo(self.string_column, self.strings_table_combo.currentData())
        self.strings_table_combo.currentTextChanged.connect(
            lambda _: self.populate_column_combo(self.string_column, self.strings_table_combo.currentData())
        )
        form.addRow("Столбец:", self.string_column)
        
        self.string_func = QComboBox()
        self.string_func.addItems([
            "UPPER - верхний регистр",
            "LOWER - нижний регистр",
            "SUBSTRING - подстрока",
            "TRIM - удалить пробелы",
            "LTRIM - удалить слева",
            "RTRIM - удалить справа",
            "LPAD - дополнить слева",
            "RPAD - дополнить справа",
            "CONCAT - объединить",
            "|| - оператор объединения"
        ])
        self.string_func.currentTextChanged.connect(self.update_string_params)
        form.addRow("Функция:", self.string_func)
        
        self.string_param1 = QLineEdit()
        self.string_param1.setPlaceholderText("Параметр 1")
        form.addRow("Параметр 1:", self.string_param1)
        
        self.string_param2 = QLineEdit()
        self.string_param2.setPlaceholderText("Параметр 2")
        form.addRow("Параметр 2:", self.string_param2)
        
        layout.addLayout(form)
        
        btn_execute = QPushButton("Применить функцию")
        btn_execute.clicked.connect(self.execute_strings)
        layout.addWidget(btn_execute)
        
        layout.addStretch()
    
    def setup_join_tab(self, tab):
        """Настройка вкладки JOIN"""
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        form = QFormLayout()
        
        self.join_type = QComboBox()
        self.join_type.addItems(["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN"])
        form.addRow("Тип JOIN:", self.join_type)
        
        tables = self.get_schema_tables()
        if not tables:
            tables = ["experiments"]
        
        self.join_table1 = QComboBox()
        for table in tables:
            self.join_table1.addItem(table, table)
        form.addRow("Таблица 1:", self.join_table1)
        
        self.join_table2 = QComboBox()
        for table in tables:
            self.join_table2.addItem(table, table)
        form.addRow("Таблица 2:", self.join_table2)
        
        self.join_field1 = QComboBox()
        self.join_field2 = QComboBox()
        form.addRow("Поле таблицы 1:", self.join_field1)
        form.addRow("Поле таблицы 2:", self.join_field2)
        
        self.join_table1.currentTextChanged.connect(lambda _: self.populate_join_fields(self.join_table1, self.join_field1))
        self.join_table2.currentTextChanged.connect(lambda _: self.populate_join_fields(self.join_table2, self.join_field2))
        self.populate_join_fields(self.join_table1, self.join_field1)
        self.populate_join_fields(self.join_table2, self.join_field2)
        
        self.join_columns = QTextEdit()
        self.join_columns.setPlaceholderText("t1.*, t2.* или перечислите нужные поля")
        self.join_columns.setMaximumHeight(60)
        form.addRow("Столбцы:", self.join_columns)
        
        layout.addLayout(form)
        
        btn_execute = QPushButton("Выполнить JOIN")
        btn_execute.clicked.connect(self.execute_join)
        layout.addWidget(btn_execute)
        
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

    def populate_column_combo(self, combo, table_name):
        combo.clear()
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
        elif "CONCAT" in func or "||" in func:
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
        where = self.where_text.text().strip()
        if where:
            query += f" WHERE {where}"
        
        # GROUP BY
        group_by = self.group_by_text.text().strip()
        if group_by:
            query += f" GROUP BY {group_by}"
        
        # HAVING
        having = self.having_text.text().strip()
        if having:
            query += f" HAVING {having}"
        
        # ORDER BY
        order_by = self.order_by_text.text().strip()
        if order_by:
            query += f" ORDER BY {order_by}"
        
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
        search_type = self.search_type.currentText()
        
        if not pattern:
            QMessageBox.warning(self, "Ошибка", "Введите шаблон поиска")
            return
        
        # Определяем оператор
        if "LIKE" in search_type:
            operator = "LIKE" if "ILIKE" not in search_type else "ILIKE"
            pattern = f"'{pattern}'"
        elif "~*" in search_type:
            operator = "~*"
            pattern = f"'{pattern}'"
        elif "!~*" in search_type:
            operator = "!~*"
            pattern = f"'{pattern}'"
        elif "!~" in search_type:
            operator = "!~"
            pattern = f"'{pattern}'"
        else:  # ~
            operator = "~"
            pattern = f"'{pattern}'"
        
        table = self.search_table_combo.currentData() or "experiments"
        col_expr = f"({quote_ident(column)}::text)" if operator in ("LIKE", "ILIKE") or "~~" in operator else quote_ident(column)
        query = f"SELECT * FROM ddos.{quote_ident(table)} WHERE {col_expr} {operator} {pattern}"
        success, data, columns = execute_custom_query(query)
        
        if success:
            self.display_results(data, columns if columns else [])
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка поиска:\n{data}")
    
    def execute_strings(self):
        """Выполнить функции работы со строками"""
        column = self.string_column.currentData()
        col_sql = quote_ident(column) if column else column
        func = self.string_func.currentText()
        param1 = self.string_param1.text().strip()
        param2 = self.string_param2.text().strip()
        
        # Строим выражение функции
        if "UPPER" in func:
            expr = f"UPPER({col_sql})"
        elif "LOWER" in func:
            expr = f"LOWER({col_sql})"
        elif "SUBSTRING" in func:
            if not param1 or not param2:
                QMessageBox.warning(self, "Ошибка", "Укажите начало и длину")
                return
            expr = f"SUBSTRING({col_sql} FROM {param1} FOR {param2})"
        elif "TRIM" in func:
            expr = f"TRIM({col_sql})"
        elif "LTRIM" in func:
            expr = f"LTRIM({col_sql})"
        elif "RTRIM" in func:
            expr = f"RTRIM({col_sql})"
        elif "LPAD" in func:
            if not param1:
                QMessageBox.warning(self, "Ошибка", "Укажите длину")
                return
            pad_char = param2 if param2 else "' '"
            expr = f"LPAD({col_sql}, {param1}, {pad_char})"
        elif "RPAD" in func:
            if not param1:
                QMessageBox.warning(self, "Ошибка", "Укажите длину")
                return
            pad_char = param2 if param2 else "' '"
            expr = f"RPAD({col_sql}, {param1}, {pad_char})"
        elif "CONCAT" in func:
            parts = [col_sql]
            if param1:
                parts.append(param1)
            if param2:
                parts.append(param2)
            expr = f"CONCAT({', '.join(parts)})"
        elif "||" in func:
            parts = [col_sql]
            if param1:
                parts.append(param1)
            if param2:
                parts.append(param2)
            expr = " || ".join(parts)
        else:
            expr = column
        
        table = self.strings_table_combo.currentData() or "experiments"
        query = f"SELECT {quote_ident(column)}, {expr} AS result FROM ddos.{quote_ident(table)}"
        success, data, columns = execute_custom_query(query)
        
        if success:
            self.display_results(data, columns if columns else [])
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка выполнения:\n{data}")
    
    def execute_join(self):
        """Выполнить JOIN"""
        join_type = self.join_type.currentText()
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

