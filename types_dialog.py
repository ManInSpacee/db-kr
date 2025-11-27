"""
Окно для работы с пользовательскими типами данных (ENUM и составные типы)
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QMessageBox, QLabel, QTabWidget,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from db import get_connection, execute_custom_query

class TypesManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление типами данных")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout()
        
        # Вкладки: Просмотр/Удаление, Создать ENUM, Создать Составной
        self.tabs = QTabWidget()
        
        # Вкладка 1: Список типов
        self.tab_list = QWidget()
        self.setup_list_tab()
        self.tabs.addTab(self.tab_list, "Список типов")
        
        # Вкладка 2: Создать ENUM
        self.tab_enum = QWidget()
        self.setup_enum_tab()
        self.tabs.addTab(self.tab_enum, "Создать ENUM")
        
        # Вкладка 3: Создать составной тип
        self.tab_composite = QWidget()
        self.setup_composite_tab()
        self.tabs.addTab(self.tab_composite, "Создать составной тип")
        
        layout.addWidget(self.tabs)
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
        
        self.setLayout(layout)
        
        # При переключении на вкладку списка обновляем его
        self.tabs.currentChanged.connect(self.on_tab_changed)
    
    def on_tab_changed(self, index):
        if index == 0:
            self.refresh_types_list()

    def setup_list_tab(self):
        layout = QVBoxLayout()
        self.tab_list.setLayout(layout)
        
        self.types_table = QTableWidget()
        self.types_table.setColumnCount(3)
        self.types_table.setHorizontalHeaderLabels(["Имя типа", "Вид", "Действие"])
        self.types_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.types_table)
        
        btn_refresh = QPushButton("Обновить список")
        btn_refresh.clicked.connect(self.refresh_types_list)
        layout.addWidget(btn_refresh)
        
        self.refresh_types_list()

    def refresh_types_list(self):
        conn = get_connection()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            # Получаем пользовательские типы из схемы ddos
            # t.typtype: 'e' - enum, 'c' - composite
            cur.execute("""
                SELECT t.typname, t.typtype
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = 'ddos' 
                  AND (t.typtype = 'e' OR t.typtype = 'c')
                  AND t.typname != 'вспомогательная' -- исключаем таблицу
            """)
            rows = cur.fetchall()
            cur.close()
            
            self.types_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                name = row[0]
                kind = "ENUM" if row[1] == 'e' else "Составной (Composite)"
                # Если это таблица, она тоже может иметь тип 'c', но мы фильтруем по логике приложения
                # (в PostgreSQL каждая таблица создает одноименный тип)
                
                self.types_table.setItem(i, 0, QTableWidgetItem(name))
                self.types_table.setItem(i, 1, QTableWidgetItem(kind))
                
                btn_drop = QPushButton("Удалить")
                btn_drop.clicked.connect(lambda checked, n=name: self.drop_type(n))
                self.types_table.setCellWidget(i, 2, btn_drop)
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить типы: {e}")

    def drop_type(self, name):
        reply = QMessageBox.question(self, "Подтверждение", f"Удалить тип '{name}'?", 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            success, _, msg = execute_custom_query(f"DROP TYPE ddos.\"{name}\"")
            if success:
                QMessageBox.information(self, "Успех", "Тип удален")
                self.refresh_types_list()
            else:
                QMessageBox.critical(self, "Ошибка", msg)

    def setup_enum_tab(self):
        layout = QVBoxLayout()
        self.tab_enum.setLayout(layout)
        
        form = QFormLayout()
        self.enum_name = QLineEdit()
        self.enum_name.setPlaceholderText("status_type")
        form.addRow("Имя типа:", self.enum_name)
        layout.addLayout(form)
        
        layout.addWidget(QLabel("Значения ENUM:"))
        self.enum_list_widget = QTableWidget(0, 1)
        self.enum_list_widget.setHorizontalHeaderLabels(["Значение"])
        self.enum_list_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.enum_list_widget)
        
        btn_layout = QHBoxLayout()
        btn_add_val = QPushButton("Добавить значение")
        btn_add_val.clicked.connect(self.add_enum_value_row)
        btn_del_val = QPushButton("Удалить выбранное")
        btn_del_val.clicked.connect(self.del_enum_value_row)
        btn_layout.addWidget(btn_add_val)
        btn_layout.addWidget(btn_del_val)
        layout.addLayout(btn_layout)
        
        btn_create = QPushButton("Создать ENUM")
        btn_create.clicked.connect(self.create_enum)
        layout.addWidget(btn_create)

    def add_enum_value_row(self):
        row = self.enum_list_widget.rowCount()
        self.enum_list_widget.insertRow(row)
        self.enum_list_widget.setItem(row, 0, QTableWidgetItem("VALUE"))

    def del_enum_value_row(self):
        row = self.enum_list_widget.currentRow()
        if row >= 0:
            self.enum_list_widget.removeRow(row)

    def create_enum(self):
        name = self.enum_name.text().strip()
        
        values_list = []
        for i in range(self.enum_list_widget.rowCount()):
            item = self.enum_list_widget.item(i, 0)
            if item and item.text().strip():
                values_list.append(item.text().strip())
        
        if not name:
            QMessageBox.warning(self, "Внимание", "Заполните имя типа")
            return
            
        if not values_list:
            QMessageBox.warning(self, "Внимание", "Добавьте хотя бы одно значение")
            return
            
        # Формируем SQL
        values_str = "', '".join(values_list)
        query = f"CREATE TYPE ddos.\"{name}\" AS ENUM ('{values_str}')"
        
        success, _, msg = execute_custom_query(query)
        if success:
            QMessageBox.information(self, "Успех", "Тип ENUM успешно создан")
            self.enum_name.clear()
            self.enum_list_widget.setRowCount(0)
            self.tabs.setCurrentIndex(0) # Переход к списку
        else:
            QMessageBox.critical(self, "Ошибка", msg)

    def setup_composite_tab(self):
        layout = QVBoxLayout()
        self.tab_composite.setLayout(layout)
        
        form = QFormLayout()
        self.comp_name = QLineEdit()
        self.comp_name.setPlaceholderText("address_type")
        form.addRow("Имя типа:", self.comp_name)
        layout.addLayout(form)
        
        layout.addWidget(QLabel("Поля составного типа:"))
        self.comp_table = QTableWidget(0, 2)
        self.comp_table.setHorizontalHeaderLabels(["Имя поля", "Тип данных"])
        self.comp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.comp_table)
        
        btn_layout = QHBoxLayout()
        btn_add_field = QPushButton("Добавить поле")
        btn_add_field.clicked.connect(self.add_comp_field_row)
        btn_del_field = QPushButton("Удалить выбранное")
        btn_del_field.clicked.connect(self.del_comp_field_row)
        btn_layout.addWidget(btn_add_field)
        btn_layout.addWidget(btn_del_field)
        layout.addLayout(btn_layout)
        
        btn_create = QPushButton("Создать составной тип")
        btn_create.clicked.connect(self.create_composite)
        layout.addWidget(btn_create)

    def add_comp_field_row(self):
        row = self.comp_table.rowCount()
        self.comp_table.insertRow(row)
        self.comp_table.setItem(row, 0, QTableWidgetItem("field_name"))
        # Для типа данных можно сделать комбобокс, но пока оставим текст для гибкости
        # или можно сделать базовый набор типов
        type_combo = QComboBox()
        type_combo.setEditable(True)
        type_combo.addItems(["integer", "varchar(255)", "text", "boolean", "date", "timestamp"])
        self.comp_table.setCellWidget(row, 1, type_combo)

    def del_comp_field_row(self):
        row = self.comp_table.currentRow()
        if row >= 0:
            self.comp_table.removeRow(row)

    def create_composite(self):
        name = self.comp_name.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Внимание", "Заполните имя типа")
            return
            
        fields_list = []
        for i in range(self.comp_table.rowCount()):
            fname_item = self.comp_table.item(i, 0)
            ftype_widget = self.comp_table.cellWidget(i, 1)
            
            if fname_item and ftype_widget:
                fname = fname_item.text().strip()
                ftype = ftype_widget.currentText().strip()
                if fname and ftype:
                    fields_list.append(f"{fname} {ftype}")
        
        if not fields_list:
            QMessageBox.warning(self, "Внимание", "Добавьте хотя бы одно поле")
            return
        
        fields_str = ",\n".join(fields_list)
        query = f"CREATE TYPE ddos.\"{name}\" AS (\n{fields_str}\n)"
        
        success, _, msg = execute_custom_query(query)
        if success:
            QMessageBox.information(self, "Успех", "Составной тип успешно создан")
            self.comp_name.clear()
            self.comp_table.setRowCount(0)
            self.tabs.setCurrentIndex(0)
        else:
            QMessageBox.critical(self, "Ошибка", f"Ошибка создания: {msg}")

