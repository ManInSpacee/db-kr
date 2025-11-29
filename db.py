"""
Функции для работы с базой данных PostgreSQL
"""
import psycopg2
import logging
import random
from datetime import datetime, timedelta
from config import DB_CONFIG, ATTACK_TYPES
#f;sgjdlkfgjkdfkg;l
# Глобальная переменная для хранения подключения
conn = None


def quote_ident(name: str) -> str:
    """Экранировать идентификатор для корректной работы с кириллицей и пробелами."""
    return f"\"{name.replace('\"', '\"\"')}\""


def get_connection():
    global conn
    
    # Если подключения нет или оно закрыто - создаем новое
    if conn is None or conn.closed:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            logging.info("Подключение к БД установлено")
        except Exception as e:
            logging.error(f"Ошибка подключения: {e}")
            return None
    
    return conn


def schema_exists():
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        # Проверяем существование схемы через information_schema
        cur.execute("""
            SELECT EXISTS(
                SELECT 1 
                FROM information_schema.schemata 
                WHERE schema_name = 'ddos'
            );
        """)
        exists = cur.fetchone()[0]
        cur.close()
        return exists
    except Exception as e:
        conn.rollback()
        logging.error(f"Ошибка проверки схемы: {e}")
        return False


def create_schema():
    """
    Создать схему базы данных с таблицами и типами
    
    Создает:
    - Схему ddos (только если не существует)
    - ENUM тип attack_type с типами атак
    - Таблицу experiments с ограничениями
    - Дополнительную таблицу "вспомогательная" для связей
    
    Returns:
        Кортеж (успех: bool, сообщение: str)
    """
    conn = get_connection()
    if not conn:
        return False, "Нет подключения к БД"
    
    # Проверяем существование схемы перед созданием
    if schema_exists():
        return False, "Схема 'ddos' уже существует. Можно создать только одну схему."
    
    try:
        cur = conn.cursor()
        
        # Создаем схему ddos (без IF NOT EXISTS, так как проверили выше)
        cur.execute("CREATE SCHEMA ddos;")
        
        # Создаем ENUM тип для типов атак
        attack_types_str = "', '".join(ATTACK_TYPES)
        cur.execute(f"""
            CREATE TYPE ddos.attack_type AS ENUM ('{attack_types_str}');
        """)
        
        # Создаем вспомогательную таблицу (под внешние ключи)
        cur.execute("""
            CREATE TABLE ddos."вспомогательная" (
                id SERIAL PRIMARY KEY,
                segment_code VARCHAR(50) NOT NULL UNIQUE,
                label VARCHAR(255) NOT NULL,
                location VARCHAR(255),
                purpose TEXT,
                criticality VARCHAR(20) CHECK (criticality IN ('LOW','MEDIUM','HIGH'))
            );
        """)
        # Можно заранее наполнить базовыми значениями для удобства
        cur.execute("""
            INSERT INTO ddos."вспомогательная"(segment_code, label, location, purpose, criticality)
            VALUES
                ('EDGE-A', 'Крайняя зона защиты', 'ЦОД Москва-1', 'Фронтовые фильтрующие узлы перед интернетом', 'HIGH'),
                ('CORE-B', 'Ядро обработки', 'ЦОД Санкт-Петербург', 'Корневые балансировщики и аналитика', 'MEDIUM'),
                ('LAB-C', 'Лабораторный стенд', 'Тестовый контур', 'Испытания новых сценариев атак', 'LOW');
        """)
        # Создаем таблицу экспериментов (после вспомогательной, чтобы работал FK)
        cur.execute("""
            CREATE TABLE ddos.experiments (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                attack_type ddos.attack_type NOT NULL,
                packets INTEGER NOT NULL CHECK (packets > 0),
                duration DECIMAL(10,2) NOT NULL CHECK (duration > 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                auxiliary_id INTEGER,
                CONSTRAINT fk_experiments_aux
                    FOREIGN KEY (auxiliary_id)
                    REFERENCES ddos."вспомогательная"(id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL
                );
        """)
        
        # Сохраняем изменения
        conn.commit()
        cur.close()
        logging.info("Схема БД создана")
        return True, "Схема успешно создана"
        
    except Exception as e:
        # Откатываем изменения при ошибке
        conn.rollback()
        logging.error(f"Ошибка создания схемы: {e}")
        return False, f"Ошибка создания схемы: {str(e)}"


def drop_schema():
    """Удалить схему ddos со всеми объектами, даже если таблицы переименованы."""
    conn = get_connection()
    if not conn:
        return False, "Нет подключения к БД"
    if not schema_exists():
        return False, "Схема 'ddos' не найдена"
    try:
        cur = conn.cursor()
        cur.execute("DROP SCHEMA ddos CASCADE;")
        conn.commit()
        cur.close()
        logging.info("Схема 'ddos' удалена")
        return True, "Все объекты схемы удалены"
    except Exception as e:
        if conn and conn.status != 1:  # not READY
            try:
                conn.rollback()
            except Exception:
                pass
        logging.error(f"Ошибка удаления схемы: {e}")
        return False, f"Ошибка удаления схемы: {str(e)}"


def insert_data(name, attack_type, packets, duration, date=None, auxiliary_id=None):
    """
    Вставить данные в таблицу experiments (Старая версия для совместимости)
    Используйте insert_dynamic_data для универсальности.
    """
    return insert_dynamic_data("experiments", {
        "name": name,
        "attack_type": attack_type,
        "packets": packets,
        "duration": duration,
        "created_at": date,
        "auxiliary_id": auxiliary_id
    })

def insert_dynamic_data(table_name, data_dict):
    """
    Динамическая вставка данных в любую таблицу.
    
    Args:
        table_name: Имя таблицы (например, 'experiments')
        data_dict: Словарь {column_name: value}
    """
    conn = get_connection()
    if not conn:
        return False, "Нет подключения к БД"
        
    try:
        cur = conn.cursor()
        
        # Фильтруем None значения (пусть база ставит NULL или DEFAULT)
        # НО! Для некоторых колонок None может быть явным NULL. 
        # Оставим как есть, psycopg2 умеет конвертировать None в NULL.
        
        cols = []
        vals = []
        placeholders = []
        
        for col, val in data_dict.items():
            cols.append(quote_ident(col))
            vals.append(val)
            placeholders.append("%s")
            
        if not cols:
            return False, "Нет данных для вставки"
            
        col_str = ", ".join(cols)
        ph_str = ", ".join(placeholders)
        
        query = f"INSERT INTO ddos.{quote_ident(table_name)} ({col_str}) VALUES ({ph_str})"
        
        cur.execute(query, tuple(vals))
        conn.commit()
        cur.close()
        return True, "Данные успешно добавлены"
        
    except Exception as e:
        conn.rollback()
        logging.error(f"Ошибка вставки в {table_name}: {e}")
        return False, str(e)


def insert_auxiliary_data(segment_code, label, location, purpose, criticality):
    """
    Вставить данные в таблицу 'вспомогательная'
    """
    conn = get_connection()
    if not conn:
        return False, "Нет подключения к БД"
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ddos."вспомогательная" (segment_code, label, location, purpose, criticality)
            VALUES (%s, %s, %s, %s, %s)
        """, (segment_code, label, location, purpose, criticality))
        conn.commit()
        cur.close()
        return True, "Цель успешно добавлена"
    except Exception as e:
        conn.rollback()
        return False, str(e)


def get_auxiliary_items():
    """Получить список записей из вспомогательной таблицы."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, segment_code, label, location, purpose, criticality
            FROM ddos."вспомогательная"
            ORDER BY label
        """)
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id": row[0],
                "segment_code": row[1],
                "label": row[2],
                "location": row[3],
                "purpose": row[4],
                "criticality": row[5]
            }
            for row in rows
        ]
    except Exception as e:
        conn.rollback()
        logging.error(f"Ошибка получения 'вспомогательная': {e}")
        return []


def get_data(attack_type_filter=None, date_from=None, date_to=None, table_name=None, extra_conditions=None):
    """
    Получить данные из таблицы с фильтрами
    table_name: имя таблицы (если None, использовать 'experiments')
    """
    conn = get_connection()
    if not conn:
        return []
    if not table_name:
        table_name = 'experiments'
    try:
        cur = conn.cursor()
        # Получить реальное описание колонок таблицы (на случай, если изменены)
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'ddos' AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        columns = [row[0] for row in cur.fetchall()]
        if not columns:
            cur.close()
            return []
        select_cols = ', '.join(quote_ident(col) for col in columns)
        table_ident = quote_ident(table_name)
        query = f'SELECT {select_cols} FROM ddos.{table_ident} WHERE 1=1'
        params = []
        # Фильтр только если attack_type реально есть среди колонок
        if attack_type_filter is not None and 'attack_type' in columns:
            query += f" AND {quote_ident('attack_type')} = %s"
            params.append(attack_type_filter)
        if date_from and 'created_at' in columns:
            query += f" AND {quote_ident('created_at')} >= %s::timestamp"
            params.append(f"{date_from} 00:00:00")
        if date_to and 'created_at' in columns:
            query += f" AND {quote_ident('created_at')} <= %s::timestamp"
            params.append(f"{date_to} 23:59:59")
        if extra_conditions:
            for cond in extra_conditions:
                if cond:
                    query += f" AND ({cond})"
        if 'created_at' in columns:
            query += f" ORDER BY {quote_ident('created_at')} DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception as e:
        conn.rollback()
        logging.error(f'Ошибка получения данных: {e}')
        return []


def get_table_columns(table_name='experiments'):
    """Получить список столбцов таблицы"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'ddos' AND table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        columns = cur.fetchall()
        cur.close()
        return columns
    except Exception as e:
        conn.rollback()
        logging.error(f"Ошибка получения столбцов: {e}")
        return []

def get_enum_labels(type_name):
    """
    Получить все возможные значения (labels) для перечислимого типа (ENUM)
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        # Ищем в ddos схеме
        cur.execute("""
            SELECT e.enumlabel
            FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            JOIN pg_namespace n ON t.typnamespace = n.oid
            WHERE t.typname = %s AND n.nspname = 'ddos'
            ORDER BY e.enumsortorder;
        """, (type_name,))
        rows = cur.fetchall()
        cur.close()
        return [r[0] for r in rows]
    except Exception as e:
        conn.rollback()
        logging.error(f"Ошибка получения значений enum {type_name}: {e}")
        return []

def get_composite_type_fields(type_name):
    """
    Получить поля составного типа (Composite Type)
    Returns: [(field_name, field_type), ...]
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.attname, format_type(a.atttypid, a.atttypmod)
            FROM pg_type t
            JOIN pg_attribute a ON a.attrelid = t.typrelid
            JOIN pg_namespace n ON t.typnamespace = n.oid
            WHERE t.typname = %s AND n.nspname = 'ddos'
            ORDER BY a.attnum;
        """, (type_name,))
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception as e:
        conn.rollback()
        logging.error(f"Ошибка получения полей составного типа {type_name}: {e}")
        return []

def execute_alter_table(sql_command):
    """
    Выполнить команду ALTER TABLE
    
    Args:
        sql_command: SQL команда ALTER TABLE
    
    Returns:
        Кортеж (успех: bool, сообщение: str)
    """
    conn = get_connection()
    if not conn:
        return False, "Нет подключения к БД"
    
    try:
        cur = conn.cursor()
        cur.execute(sql_command)
        conn.commit()
        cur.close()
        logging.info(f"ALTER TABLE выполнен: {sql_command}")
        return True, "Команда успешно выполнена"
    except Exception as e:
        # Устраняем двойной rollback при abort-транзакциях
        if conn and conn.status != 1:  # 1 == STATUS_READY
            try:
                conn.rollback()
            except Exception:
                pass
        logging.error(f"Ошибка ALTER TABLE: {e}")
        return False, str(e)


def execute_custom_query(query, params=None):
    """
    Выполнить произвольный SQL запрос
    
    Args:
        query: SQL запрос
        params: Параметры запроса
    
    Returns:
        Кортеж (успех: bool, данные: list, сообщение: str)
    """
    conn = get_connection()
    if not conn:
        return False, [], "Нет подключения к БД"
    
    try:
        cur = conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        
        # Если это SELECT - возвращаем данные
        if query.strip().upper().startswith('SELECT'):
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
            cur.close()
            return True, rows, columns
        else:
            # Для других команд - коммитим
            conn.commit()
            cur.close()
            return True, [], "Команда успешно выполнена"
    except Exception as e:
        conn.rollback()
        logging.error(f"Ошибка выполнения запроса: {e}")
        return False, [], str(e)

def generate_test_data():
    """
    Генерация тестовых данных для демонстрации функционала.
    """
    conn = get_connection()
    if not conn:
        return False, "Нет подключения к БД"
        
    if not schema_exists():
        return False, "Схема не создана. Сначала нажмите 'Создать базу'."
    
    try:
        cur = conn.cursor()
        
        # 1. Получаем список ID целей (вспомогательная таблица)
        cur.execute('SELECT id FROM ddos."вспомогательная"')
        aux_ids = [row[0] for row in cur.fetchall()]
        
        # Если целей нет, создаем пару дефолтных
        if not aux_ids:
            cur.execute("""
                INSERT INTO ddos."вспомогательная"(segment_code, label, location, purpose, criticality)
                VALUES
                    ('TEST-A', 'Тестовый сервер 1', 'Москва', 'Тесты', 'LOW'),
                    ('PROD-B', 'Продакшн сервер', 'СПб', 'Клиенты', 'HIGH')
                RETURNING id
            """)
            aux_ids = [row[0] for row in cur.fetchall()]
        
        # 2. Генерируем 15 случайных экспериментов
        # Проверяем, какие колонки реально существуют
        real_cols = [c[0] for c in get_table_columns('experiments')]
        
        for i in range(15):
            attack = random.choice(ATTACK_TYPES)
            packets = random.randint(100, 50000)
            duration = round(random.uniform(1.0, 60.0), 2)
            
            # Случайная дата за последний месяц
            days_ago = random.randint(0, 30)
            date_val = datetime.now() - timedelta(days=days_ago)
            date_str = date_val.strftime("%Y-%m-%d")
            
            # Случайная цель (иногда NULL)
            aux_id = random.choice(aux_ids + [None])
            
            name = f"AutoTest_{attack}_{i}_{random.randint(1000,9999)}"
            
            # Собираем данные только для существующих колонок
            data = {}
            if 'name' in real_cols: data['name'] = name
            if 'attack_type' in real_cols: data['attack_type'] = attack
            if 'packets' in real_cols: data['packets'] = packets
            if 'duration' in real_cols: data['duration'] = duration
            if 'created_at' in real_cols: data['created_at'] = date_str
            if 'auxiliary_id' in real_cols: data['auxiliary_id'] = aux_id
            
            insert_dynamic_data("experiments", data)
            
        return True, "Тестовые данные успешно сгенерированы (15 записей)"
        
    except Exception as e:
        return False, f"Ошибка генерации: {e}"
