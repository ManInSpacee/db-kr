"""
Конфигурация приложения
"""
#sdifjldskfj
# Параметры подключения к базе данных PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'klim'
}

# Список типов DDoS атак (должен совпадать с ENUM в БД)
ATTACK_TYPES = ['SYN_FLOOD', 'UDP_FLOOD', 'HTTP_FLOOD']

