"""
Функции для работы с базой данных PostgreSQL
"""
import psycopg2
import logging
from config import DB_CONFIG, ATTACK_TYPES

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
        
        # Создаем таблицу экспериментов
        # PRIMARY KEY - первичный ключ (id)
        # UNIQUE - уникальность имени
        # NOT NULL - обязательное поле
        # CHECK - проверка значений (packets > 0, duration > 0)
        cur.execute("""
            CREATE TABLE ddos.experiments (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                attack_type ddos.attack_type NOT NULL,
                packets INTEGER NOT NULL CHECK (packets > 0),
                duration DECIMAL(10,2) NOT NULL CHECK (duration > 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Создаем вспомогательную таблицу (под внешние ключи)
        cur.execute("""
            CREATE TABLE ddos."вспомогательная" (
                id SERIAL PRIMARY KEY,
                label VARCHAR(255) NOT NULL,
                description TEXT
            );
        """)
        # Можно заранее наполнить базовыми значениями для удобства
        cur.execute("""
            INSERT INTO ddos."вспомогательная"(label, description)
            VALUES
                ('Сегмент А', 'Базовый сегмент инфраструктуры'),
                ('Сегмент B', 'Дополнительный сегмент');
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


def insert_data(name, attack_type, packets, duration, date=None):
    """
    Вставить данные в таблицу experiments
    
    Args:
        name: Название эксперимента
        attack_type: Тип атаки (из ATTACK_TYPES)
        packets: Количество пакетов
        duration: Длительность в секундах
        date: Дата в формате YYYY-MM-DD (если None - используется текущая дата)
    
    Returns:
        Кортеж (успех: bool, сообщение: str)
    """
    conn = get_connection()
    if not conn:
        return False, "Нет подключения к БД"
    
    try:
        cur = conn.cursor()
        
        # Если дата указана - используем её, иначе текущая дата/время
        if date:
            cur.execute("""
                INSERT INTO ddos.experiments (name, attack_type, packets, duration, created_at)
                VALUES (%s, %s, %s, %s, %s::timestamp)
            """, (name, attack_type, int(packets), float(duration), date))
        else:
            cur.execute("""
                INSERT INTO ddos.experiments (name, attack_type, packets, duration)
                VALUES (%s, %s, %s, %s)
            """, (name, attack_type, int(packets), float(duration)))
        
        # Сохраняем изменения
        conn.commit()
        cur.close()
        logging.info(f"Данные добавлены: {name}")
        return True, "Данные успешно добавлены"
        
    except Exception as e:
        # Откатываем изменения при ошибке
        conn.rollback()
        logging.error(f"Ошибка вставки: {e}")
        return False, str(e)


def get_data(attack_type_filter=None, date_from=None, date_to=None, table_name=None):
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
        if 'created_at' in columns:
            query += f" ORDER BY {quote_ident('created_at')} DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    except Exception as e:
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
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'ddos' AND table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        columns = cur.fetchall()
        cur.close()
        return columns
    except Exception as e:
        logging.error(f"Ошибка получения столбцов: {e}")
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

