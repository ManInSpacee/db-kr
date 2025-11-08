"""
Окно для работы с ALTER TABLE
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QMessageBox, QLabel, QCheckBox
)
from db import execute_alter_table, get_table_columns


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
        
        self.table_edit = QLineEdit()
        self.table_edit.setText("experiments")
        form.addRow("Таблица:", self.table_edit)
        
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
    
    def update_form(self):
        """Обновить форму в зависимости от выбранной операции"""
        # Очищаем динамическую форму
        while self.dynamic_form.rowCount() > 0:
            self.dynamic_form.removeRow(0)
        self.dynamic_widgets.clear()
        
        operation = self.operation_combo.currentText()
        
        if operation == "Добавить столбец":
            self.dynamic_widgets['column_name'] = QLineEdit()
            self.dynamic_widgets['column_type'] = QLineEdit()
            self.dynamic_widgets['not_null'] = QCheckBox()
            self.dynamic_form.addRow("Имя столбца:", self.dynamic_widgets['column_name'])
            self.dynamic_form.addRow("Тип данных:", self.dynamic_widgets['column_type'])
            self.dynamic_form.addRow("NOT NULL:", self.dynamic_widgets['not_null'])
            
        elif operation == "Удалить столбец":
            self.dynamic_widgets['column_name'] = QLineEdit()
            self.dynamic_form.addRow("Имя столбца:", self.dynamic_widgets['column_name'])
            
        elif operation == "Переименовать столбец":
            self.dynamic_widgets['old_name'] = QLineEdit()
            self.dynamic_widgets['new_name'] = QLineEdit()
            self.dynamic_form.addRow("Старое имя:", self.dynamic_widgets['old_name'])
            self.dynamic_form.addRow("Новое имя:", self.dynamic_widgets['new_name'])
            
        elif operation == "Изменить тип данных":
            self.dynamic_widgets['column_name'] = QLineEdit()
            self.dynamic_widgets['new_type'] = QLineEdit()
            self.dynamic_form.addRow("Имя столбца:", self.dynamic_widgets['column_name'])
            self.dynamic_form.addRow("Новый тип:", self.dynamic_widgets['new_type'])
            
        elif operation == "Добавить ограничение":
            self.dynamic_widgets['constraint_name'] = QLineEdit()
            self.dynamic_widgets['constraint_type'] = QComboBox()
            self.dynamic_widgets['constraint_type'].addItems(['CHECK', 'UNIQUE', 'NOT NULL', 'FOREIGN KEY'])
            self.dynamic_widgets['constraint_def'] = QLineEdit()
            self.dynamic_form.addRow("Имя ограничения:", self.dynamic_widgets['constraint_name'])
            self.dynamic_form.addRow("Тип:", self.dynamic_widgets['constraint_type'])
            self.dynamic_form.addRow("Определение:", self.dynamic_widgets['constraint_def'])
            
        elif operation == "Удалить ограничение":
            self.dynamic_widgets['constraint_name'] = QLineEdit()
            self.dynamic_form.addRow("Имя ограничения:", self.dynamic_widgets['constraint_name'])
            
        elif operation == "Переименовать таблицу":
            self.dynamic_widgets['new_name'] = QLineEdit()
            self.dynamic_form.addRow("Новое имя:", self.dynamic_widgets['new_name'])
    
    def build_sql(self):
        """Построить SQL команду"""
        operation = self.operation_combo.currentText()
        table = self.table_edit.text().strip()
        
        if not table:
            return None
        
        table_full = f"ddos.{table}"
        
        if operation == "Добавить столбец":
            col_name = self.dynamic_widgets.get('column_name', QLineEdit()).text().strip()
            col_type = self.dynamic_widgets.get('column_type', QLineEdit()).text().strip()
            not_null = self.dynamic_widgets.get('not_null', QCheckBox()).isChecked()
            if not col_name or not col_type:
                return None
            sql = f"ALTER TABLE {table_full} ADD COLUMN {col_name} {col_type}"
            if not_null:
                sql += " NOT NULL"
            return sql
            
        elif operation == "Удалить столбец":
            col_name = self.dynamic_widgets.get('column_name', QLineEdit()).text().strip()
            if not col_name:
                return None
            return f"ALTER TABLE {table_full} DROP COLUMN {col_name}"
            
        elif operation == "Переименовать столбец":
            old_name = self.dynamic_widgets.get('old_name', QLineEdit()).text().strip()
            new_name = self.dynamic_widgets.get('new_name', QLineEdit()).text().strip()
            if not old_name or not new_name:
                return None
            return f"ALTER TABLE {table_full} RENAME COLUMN {old_name} TO {new_name}"
            
        elif operation == "Изменить тип данных":
            col_name = self.dynamic_widgets.get('column_name', QLineEdit()).text().strip()
            new_type = self.dynamic_widgets.get('new_type', QLineEdit()).text().strip()
            if not col_name or not new_type:
                return None
            return f"ALTER TABLE {table_full} ALTER COLUMN {col_name} TYPE {new_type}"
            
        elif operation == "Добавить ограничение":
            const_name = self.dynamic_widgets.get('constraint_name', QLineEdit()).text().strip()
            const_type = self.dynamic_widgets.get('constraint_type', QComboBox()).currentText()
            const_def = self.dynamic_widgets.get('constraint_def', QLineEdit()).text().strip()
            if not const_name:
                return None
            if const_type == "NOT NULL":
                col_name = const_def.strip()
                if not col_name:
                    return None
                return f"ALTER TABLE {table_full} ALTER COLUMN {col_name} SET NOT NULL"
            elif const_type == "CHECK":
                if not const_def:
                    return None
                return f"ALTER TABLE {table_full} ADD CONSTRAINT {const_name} CHECK ({const_def})"
            elif const_type == "UNIQUE":
                col_name = const_def.strip()
                if not col_name:
                    return None
                return f"ALTER TABLE {table_full} ADD CONSTRAINT {const_name} UNIQUE ({col_name})"
            elif const_type == "FOREIGN KEY":
                if not const_def:
                    return None
                return f"ALTER TABLE {table_full} ADD CONSTRAINT {const_name} FOREIGN KEY {const_def}"
            
        elif operation == "Удалить ограничение":
            const_name = self.dynamic_widgets.get('constraint_name', QLineEdit()).text().strip()
            if not const_name:
                return None
            return f"ALTER TABLE {table_full} DROP CONSTRAINT {const_name}"
            
        elif operation == "Переименовать таблицу":
            new_name = self.dynamic_widgets.get('new_name', QLineEdit()).text().strip()
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

