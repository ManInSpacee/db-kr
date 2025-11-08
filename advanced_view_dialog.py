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
from db import execute_custom_query, get_table_columns


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
        
        form = QFormLayout()
        
        self.search_column = QComboBox()
        self.search_column.addItems(["name", "attack_type"])
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
        
        form = QFormLayout()
        
        self.string_column = QComboBox()
        self.string_column.addItems(["name"])
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
        
        self.join_table1 = QLineEdit()
        self.join_table1.setText("experiments")
        form.addRow("Таблица 1:", self.join_table1)
        
        self.join_table2 = QLineEdit()
        self.join_table2.setPlaceholderText("experiments")
        form.addRow("Таблица 2:", self.join_table2)
        
        self.join_on = QLineEdit()
        self.join_on.setPlaceholderText("t1.id = t2.id")
        form.addRow("Условие ON:", self.join_on)
        
        self.join_columns = QTextEdit()
        self.join_columns.setPlaceholderText("t1.id, t1.name, t2.packets")
        self.join_columns.setMaximumHeight(60)
        form.addRow("Столбцы:", self.join_columns)
        
        layout.addLayout(form)
        
        btn_execute = QPushButton("Выполнить JOIN")
        btn_execute.clicked.connect(self.execute_join)
        layout.addWidget(btn_execute)
        
        layout.addStretch()
    
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
        
        query = f"SELECT {columns} FROM ddos.experiments"
        
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
        column = self.search_column.currentText()
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
        
        query = f"SELECT * FROM ddos.experiments WHERE {column} {operator} {pattern}"
        success, data, columns = execute_custom_query(query)
        
        if success:
            self.display_results(data, columns if columns else [])
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка поиска:\n{data}")
    
    def execute_strings(self):
        """Выполнить функции работы со строками"""
        column = self.string_column.currentText()
        func = self.string_func.currentText()
        param1 = self.string_param1.text().strip()
        param2 = self.string_param2.text().strip()
        
        # Строим выражение функции
        if "UPPER" in func:
            expr = f"UPPER({column})"
        elif "LOWER" in func:
            expr = f"LOWER({column})"
        elif "SUBSTRING" in func:
            if not param1 or not param2:
                QMessageBox.warning(self, "Ошибка", "Укажите начало и длину")
                return
            expr = f"SUBSTRING({column} FROM {param1} FOR {param2})"
        elif "TRIM" in func:
            expr = f"TRIM({column})"
        elif "LTRIM" in func:
            expr = f"LTRIM({column})"
        elif "RTRIM" in func:
            expr = f"RTRIM({column})"
        elif "LPAD" in func:
            if not param1:
                QMessageBox.warning(self, "Ошибка", "Укажите длину")
                return
            pad_char = param2 if param2 else "' '"
            expr = f"LPAD({column}, {param1}, {pad_char})"
        elif "RPAD" in func:
            if not param1:
                QMessageBox.warning(self, "Ошибка", "Укажите длину")
                return
            pad_char = param2 if param2 else "' '"
            expr = f"RPAD({column}, {param1}, {pad_char})"
        elif "CONCAT" in func:
            parts = [column]
            if param1:
                parts.append(param1)
            if param2:
                parts.append(param2)
            expr = f"CONCAT({', '.join(parts)})"
        elif "||" in func:
            parts = [column]
            if param1:
                parts.append(param1)
            if param2:
                parts.append(param2)
            expr = " || ".join(parts)
        else:
            expr = column
        
        query = f"SELECT {column}, {expr} AS result FROM ddos.experiments"
        success, data, columns = execute_custom_query(query)
        
        if success:
            self.display_results(data, columns if columns else [])
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка выполнения:\n{data}")
    
    def execute_join(self):
        """Выполнить JOIN"""
        join_type = self.join_type.currentText()
        table1 = self.join_table1.text().strip()
        table2 = self.join_table2.text().strip()
        on_condition = self.join_on.text().strip()
        columns = self.join_columns.toPlainText().strip()
        
        if not table1 or not table2:
            QMessageBox.warning(self, "Ошибка", "Укажите обе таблицы")
            return
        
        if not on_condition:
            QMessageBox.warning(self, "Ошибка", "Укажите условие ON")
            return
        
        if not columns:
            columns = "*"
        
        query = f"SELECT {columns} FROM ddos.{table1} t1 {join_type} ddos.{table2} t2 ON {on_condition}"
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

