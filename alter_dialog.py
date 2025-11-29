"""
Окно для работы с ALTER TABLE
"""
import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QMessageBox, QLabel, QCheckBox
)
from db import execute_alter_table, get_table_columns, get_connection

#trash...
# Словарь сопоставления: отображаемое имя ↔ SQL-имя (двустороннее)
COLUMN_LABELS = {
    'id': 'ID',
    'name': 'Название',
    'attack_type': 'Тип атаки',
    'packets': 'Пакетов',
    'duration': 'Длительность',
    'created_at': 'Дата',
    'auxiliary_id': 'Инфраструктура',
    'segment_code': 'Код сегмента',
    'label': 'Название сегмента',
    'location': 'Расположение',
    'purpose': 'Назначение',
    'criticality': 'Критичность',
}
REVERSE_COLUMN_LABELS = {v.lower(): k for k, v in COLUMN_LABELS.items()}

def resolve_column_name(user_text):
    """Нормализует и возвращает SQL-имя по пользовательскому (или оригинал)"""
    user_text = user_text.strip().lower()
    return REVERSE_COLUMN_LABELS.get(user_text, user_text)


def quote_identifier(name: str) -> str:
    """Экранировать идентификатор для использования в SQL (сохраняет регистр и кириллицу)."""
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def normalize_expression(expr: str) -> str:
    """Подготовить выражение CHECK: убрать WHERE, заменить видимые названия столбцов на SQL-имена."""
    expr = expr.strip()
    if expr.lower().startswith("where "):
        expr = expr[6:].strip()
    for sql_name, label in COLUMN_LABELS.items():
        pattern = re.compile(rf"\b{re.escape(label)}\b", flags=re.IGNORECASE)
        expr = pattern.sub(sql_name, expr)
    return expr

class AlterTableDialog(QDialog):
    """Окно для изменения структуры таблицы"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Изменение структуры таблицы")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout()
        
        # Выбор операции
        form = QFormLayout()
        
        self.operation_combo = QComboBox()
        self.operation_combo.addItems([
            "Добавить столбец",
            "Удалить столбец",
            "Переименовать столбец",
            "Изменить тип данных",
            "Добавить ограничение",
            "Удалить ограничение",
            "Переименовать таблицу"
        ])
        self.operation_combo.currentTextChanged.connect(self.update_form)
        form.addRow("Операция:", self.operation_combo)
        
        # Замена QLineEdit на QComboBox для выбора таблицы
        self.table_combo = QComboBox()
        self.populate_tables()
        self.table_combo.currentTextChanged.connect(self.update_form)
        form.addRow("Таблица:", self.table_combo)
        
        layout.addLayout(form)
        
        # Динамическая форма
        self.dynamic_form = QFormLayout()
        self.dynamic_widgets = {}
        layout.addLayout(self.dynamic_form)
        
        # SQL предпросмотр
        layout.addWidget(QLabel("SQL команда:"))
        self.sql_preview = QTextEdit()
        self.sql_preview.setMaximumHeight(100)
        self.sql_preview.setReadOnly(True)
        layout.addWidget(self.sql_preview)
        
        # Кнопки
        buttons = QHBoxLayout()
        btn_preview = QPushButton("Предпросмотр SQL")
        btn_preview.clicked.connect(self.preview_sql)
        btn_execute = QPushButton("Выполнить")
        btn_execute.clicked.connect(self.execute)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        
        buttons.addWidget(btn_preview)
        buttons.addWidget(btn_execute)
        buttons.addWidget(btn_cancel)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
        self.update_form()

    def populate_tables(self):
        """Заполнить список таблиц"""
        tables = self.get_existing_tables()
        self.table_combo.clear()
        if tables:
            self.table_combo.addItems(tables)
        else:
            self.table_combo.addItem("experiments")
    
    def get_existing_tables(self):
        conn = get_connection()
        if not conn:
            return []
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='ddos' AND table_type='BASE TABLE' "
                "ORDER BY table_name"
            )
            tables = [row[0] for row in cur.fetchall()]
            cur.close()
            return tables
        except Exception:
            return []

    def get_user_types(self):
        """Получить список пользовательских типов (ENUM и COMPOSITE)"""
        conn = get_connection()
        if not conn:
            return []
        try:
            cur = conn.cursor()
            # typtype: 'e' = enum, 'c' = composite
            # Также важно исключить системные типы (начинаются с _)
            cur.execute("""
                SELECT t.typname, t.typtype
                FROM pg_type t
                JOIN pg_namespace n ON t.typnamespace = n.oid
                WHERE n.nspname = 'ddos' 
                  AND (t.typtype = 'e' OR (t.typtype = 'c' AND t.typrelid != 0))
                  AND t.typname NOT LIKE '%%[]'
                ORDER BY t.typname
            """)
            # Возвращаем список кортежей (имя, тип)
            types = [(row[0], row[1]) for row in cur.fetchall()]
            cur.close()
            return types
        except Exception:
            return []

    def get_effective_table(self):
        """Вернуть текущую выбранную таблицу."""
        return self.table_combo.currentText()

    def get_constraints_for_table(self, table_name):
        conn = get_connection()
        if not conn:
            return []
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = 'ddos' AND table_name = %s
                ORDER BY constraint_name
                """,
                (table_name,),
            )
            names = [row[0] for row in cur.fetchall()]
            cur.close()
            return names
        except Exception:
            return []

    def widget_value(self, key, default=""):
        widget = self.dynamic_widgets.get(key)
        if widget is None:
            return default
        if isinstance(widget, QComboBox):
            # Если у нас есть userData (например, для ENUM типов), берем его
            # Но только если текущий текст совпадает с текстом элемента (пользователь не отредактировал его)
            idx = widget.currentIndex()
            if idx >= 0 and widget.itemText(idx) == widget.currentText():
                data = widget.itemData(idx)
                if data is not None:
                    return data
            
            # Иначе возвращаем то, что написано (для ручного ввода типа INTEGER и т.д.)
            return widget.currentText()
        if isinstance(widget, QLineEdit):
            return widget.text()
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        return default
    
    def make_type_combo(self):
        """Создать ComboBox с типами данных (стандартные + пользовательские)"""
        combo = QComboBox()
        combo.setEditable(True)
        
        # Стандартные
        standard_types = [
            "INTEGER", "VARCHAR(255)", "TEXT", "BOOLEAN", 
            "TIMESTAMP", "DECIMAL(10,2)", "DATE"
        ]
        combo.addItems(standard_types)
        
        # Разделитель
        combo.insertSeparator(len(standard_types))
        
        # Пользовательские
        user_types = self.get_user_types()
        for name, typtype in user_types:
            # typtype 'e' -> ENUM, 'c' -> COMPOSITE
            label_suffix = "ENUM" if typtype == 'e' else "COMPOSITE"
            # Экранируем имя типа в кавычки для безопасности
            safe_type_name = f'ddos."{name}"'
            combo.addItem(f"{name} ({label_suffix})", safe_type_name)
            
        return combo

    def update_form(self):
        # Очищаем динамическую форму и виджеты
        while self.dynamic_form.rowCount() > 0:
            self.dynamic_form.removeRow(0)
        self.dynamic_widgets.clear()
        operation = self.operation_combo.currentText()
        # Для некоторых операций нужны названия столбцов (например, ограничения)
        current_table = self.get_effective_table()
        columns_info = get_table_columns(current_table)
        colnames = [col[0] for col in columns_info] if columns_info else []
        column_combo = lambda: self.make_column_combo(colnames)
        
        if operation == "Добавить столбец":
            self.dynamic_widgets['column_name'] = QLineEdit()
            self.dynamic_widgets['column_type'] = self.make_type_combo()
            self.dynamic_form.addRow("Имя столбца:", self.dynamic_widgets['column_name'])
            self.dynamic_form.addRow("Тип данных:", self.dynamic_widgets['column_type'])
        elif operation == "Удалить столбец":
            self.dynamic_widgets['column_name'] = column_combo()
            self.dynamic_form.addRow("Имя столбца:", self.dynamic_widgets['column_name'])
        elif operation == "Переименовать столбец":
            self.dynamic_widgets['old_name'] = column_combo()
            self.dynamic_widgets['new_name'] = QLineEdit()
            self.dynamic_form.addRow("Старое имя:", self.dynamic_widgets['old_name'])
            self.dynamic_form.addRow("Новое имя:", self.dynamic_widgets['new_name'])
        elif operation == "Изменить тип данных":
            self.dynamic_widgets['column_name'] = column_combo()
            self.dynamic_widgets['new_type'] = self.make_type_combo()
            self.dynamic_form.addRow("Имя столбца:", self.dynamic_widgets['column_name'])
            self.dynamic_form.addRow("Новый тип:", self.dynamic_widgets['new_type'])
        elif operation == "Добавить ограничение":
            self.dynamic_widgets['constraint_name'] = QLineEdit()
            self.dynamic_widgets['constraint_type'] = QComboBox()
            self.dynamic_widgets['constraint_type'].addItems(['CHECK', 'UNIQUE', 'NOT NULL', 'FOREIGN KEY'])
            # Вложенная логика от выбора типа ограничения
            self.dynamic_widgets['constraint_type'].currentTextChanged.connect(self.update_constraint_form)
            self.dynamic_form.addRow("Имя ограничения:", self.dynamic_widgets['constraint_name'])
            self.dynamic_form.addRow("Тип:", self.dynamic_widgets['constraint_type'])
            # Создаём контейнер для вложенной формы
            self.constraint_extra_form = QFormLayout()
            self.dynamic_form.addRow(self.constraint_extra_form)
            self.update_constraint_form()
        elif operation == "Удалить ограничение":
            constraints = self.get_constraints_for_table(current_table)
            combo = QComboBox()
            for name in constraints:
                combo.addItem(name, name)
            self.dynamic_widgets['constraint_name'] = combo
            self.dynamic_form.addRow("Имя ограничения:", self.dynamic_widgets['constraint_name'])
        elif operation == "Переименовать таблицу":
            self.dynamic_widgets['new_name'] = QLineEdit()
            self.dynamic_form.addRow("Новое имя:", self.dynamic_widgets['new_name'])
    
    def make_column_combo(self, colnames):
        from PySide6.QtWidgets import QComboBox
        combo = QComboBox()
        for col in colnames:
            label = COLUMN_LABELS.get(col, col)
            combo.addItem(label, col)
        return combo

    def update_constraint_form(self):
        # Очищаем все предыдущие поля вложенной constraint-формы
        while self.constraint_extra_form.rowCount() > 0:
            self.constraint_extra_form.removeRow(0)
        ctype = self.dynamic_widgets['constraint_type'].currentText()
        current_table = self.get_effective_table()
        columns_info = get_table_columns(current_table)
        colnames = [col[0] for col in columns_info] if columns_info else []
        from PySide6.QtWidgets import QComboBox, QLineEdit
        # NOT NULL
        if ctype == "NOT NULL":
            self.dynamic_widgets['col_notnull'] = self.make_column_combo(colnames)
            self.constraint_extra_form.addRow("Столбец:", self.dynamic_widgets['col_notnull'])
        # UNIQUE
        elif ctype == "UNIQUE":
            self.dynamic_widgets['col_unique'] = self.make_column_combo(colnames)
            self.constraint_extra_form.addRow("Столбец:", self.dynamic_widgets['col_unique'])
        # CHECK
        elif ctype == "CHECK":
            self.dynamic_widgets['def_check'] = QLineEdit()
            self.constraint_extra_form.addRow("Определение:", self.dynamic_widgets['def_check'])
        # FOREIGN KEY
        elif ctype == "FOREIGN KEY":
            self.dynamic_widgets['col_fk'] = self.make_column_combo(colnames)
            # Получаем список чужих таблиц клиента
            tables = self.get_existing_tables()
            fk_targets = [t for t in tables if t != current_table]
            if not fk_targets:
                fk_targets = tables
            self.dynamic_widgets['to_table'] = QComboBox()
            for table_name in fk_targets:
                display = table_name
                self.dynamic_widgets['to_table'].addItem(display, table_name)
            # получить для целевой таблицы столбцы, реагировать на выбор
            def _update_to_column():
                tab = self.widget_value('to_table')
                tocols = ["id"]
                if tab:
                    colinfo = get_table_columns(tab)
                    tocols = [c[0] for c in colinfo] if colinfo else ["id"]
                self.dynamic_widgets['to_column'].clear()
                for col in tocols:
                    self.dynamic_widgets['to_column'].addItem(col, col)
            self.dynamic_widgets['to_column'] = QComboBox()
            self.dynamic_widgets['to_table'].currentTextChanged.connect(_update_to_column)
            _update_to_column()
            self.dynamic_widgets['on_delete'] = QComboBox()
            self.dynamic_widgets['on_delete'].addItems(['NO ACTION','CASCADE','SET NULL','SET DEFAULT','RESTRICT'])
            self.dynamic_widgets['on_update'] = QComboBox()
            self.dynamic_widgets['on_update'].addItems(['NO ACTION','CASCADE','SET NULL','SET DEFAULT','RESTRICT'])
            self.constraint_extra_form.addRow("Столбец:", self.dynamic_widgets['col_fk'])
            self.constraint_extra_form.addRow("Ссылаемая таблица:", self.dynamic_widgets['to_table'])
            self.constraint_extra_form.addRow("Ссылаемый столбец:", self.dynamic_widgets['to_column'])
            self.constraint_extra_form.addRow("ON DELETE:", self.dynamic_widgets['on_delete'])
            self.constraint_extra_form.addRow("ON UPDATE:", self.dynamic_widgets['on_update'])

    def build_sql(self):
        operation = self.operation_combo.currentText()
        table = self.get_effective_table()
        if not table:
            return None
        table_full = f"ddos.{quote_identifier(table)}"
        if operation == "Добавить ограничение":
            const_name = self.widget_value('constraint_name').strip()
            ctype = self.widget_value('constraint_type')
            if not const_name:
                return None
            quoted_name = quote_identifier(const_name)
            if ctype == "NOT NULL":
                col = resolve_column_name(self.widget_value('col_notnull').strip())
                if not col:
                    return None
                return f"ALTER TABLE {table_full} ALTER COLUMN {quote_identifier(col)} SET NOT NULL"
            if ctype == "UNIQUE":
                col = resolve_column_name(self.widget_value('col_unique').strip())
                if not col:
                    return None
                return f"ALTER TABLE {table_full} ADD CONSTRAINT {quoted_name} UNIQUE({quote_identifier(col)})"
            if ctype == "CHECK":
                expr = normalize_expression(self.widget_value('def_check'))
                if not expr:
                    return None
                return f"ALTER TABLE {table_full} ADD CONSTRAINT {quoted_name} CHECK ({expr})"
            if ctype == "FOREIGN KEY":
                from_col = resolve_column_name(self.widget_value('col_fk').strip())
                to_table = self.widget_value('to_table')
                to_col = self.widget_value('to_column')
                on_delete = self.widget_value('on_delete').strip()
                on_update = self.widget_value('on_update').strip()
                if not from_col or not to_table or not to_col:
                    return None
                to_table_sql = quote_identifier(to_table)
                to_col_sql = quote_identifier(to_col)
                statement = (
                    f"ALTER TABLE {table_full} ADD CONSTRAINT {quoted_name} "
                    f"FOREIGN KEY ({quote_identifier(from_col)}) REFERENCES ddos.{to_table_sql}({to_col_sql})"
                )
                if on_delete and on_delete != 'NO ACTION':
                    statement += f" ON DELETE {on_delete}"
                if on_update and on_update != 'NO ACTION':
                    statement += f" ON UPDATE {on_update}"
                return statement
        elif operation == "Добавить столбец":
            col_name = resolve_column_name(self.widget_value('column_name').strip())
            col_type = self.widget_value('column_type').strip()
            if not col_name or not col_type:
                return None
            sql = f"ALTER TABLE {table_full} ADD COLUMN {quote_identifier(col_name)} {col_type}"
            return sql
            
        elif operation == "Удалить столбец":
            col_name = resolve_column_name(self.widget_value('column_name').strip())
            if not col_name:
                return None
            return f"ALTER TABLE {table_full} DROP COLUMN {quote_identifier(col_name)}"
            
        elif operation == "Переименовать столбец":
            old_name = resolve_column_name(self.widget_value('old_name').strip())
            new_name = resolve_column_name(self.widget_value('new_name').strip())
            if not old_name or not new_name:
                return None
            return f"ALTER TABLE {table_full} RENAME COLUMN {quote_identifier(old_name)} TO {quote_identifier(new_name)}"
            
        elif operation == "Изменить тип данных":
            col_name = resolve_column_name(self.widget_value('column_name').strip())
            new_type = self.widget_value('new_type').strip()
            if not col_name or not new_type:
                return None
            quoted_col = quote_identifier(col_name)
            # Добавляем USING clause для автоматического приведения типов (текст -> число и т.д.)
            # Это решает ошибку "column cannot be cast automatically to type..."
            return f"ALTER TABLE {table_full} ALTER COLUMN {quoted_col} TYPE {new_type} USING {quoted_col}::{new_type}"
            
        elif operation == "Удалить ограничение":
            const_name = self.widget_value('constraint_name').strip()
            if not const_name:
                return None
            return f"ALTER TABLE {table_full} DROP CONSTRAINT {quote_identifier(const_name)}"
            
        elif operation == "Переименовать таблицу":
            new_name = self.widget_value('new_name').strip()
            if not new_name:
                return None
            return f"ALTER TABLE {table_full} RENAME TO {new_name}"
        
        return None
    
    def preview_sql(self):
        """Показать предпросмотр SQL"""
        sql = self.build_sql()
        if sql:
            self.sql_preview.setText(sql)
        else:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
    
    def execute(self):
        """Выполнить команду ALTER TABLE"""
        sql = self.build_sql()
        if not sql:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return
        
        success, msg = execute_alter_table(sql)
        if success:
            QMessageBox.information(self, "Успех", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка выполнения:\n{msg}")
