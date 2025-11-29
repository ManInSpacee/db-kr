# 📚 Полный конспект SQL и PostgreSQL

## ЧАСТЬ 1: ОСНОВЫ SQL

---

## 1. Что такое SQL?

**SQL (Structured Query Language)** — язык структурированных запросов для работы с реляционными базами данных.

**Основные операции:**
- **DDL (Data Definition Language)** — определение структуры (CREATE, ALTER, DROP)
- **DML (Data Manipulation Language)** — манипуляция данными (SELECT, INSERT, UPDATE, DELETE)
- **DCL (Data Control Language)** — управление доступом (GRANT, REVOKE)
- **TCL (Transaction Control Language)** — управление транзакциями (COMMIT, ROLLBACK)

---

## 2. Типы данных SQL

### Числовые типы:
```sql
INTEGER          -- Целое число (-2,147,483,648 до 2,147,483,647)
BIGINT           -- Большое целое число
SMALLINT         -- Маленькое целое (-32,768 до 32,767)
DECIMAL(10,2)    -- Точное десятичное (10 цифр, 2 после запятой)
NUMERIC(5,2)     -- Аналог DECIMAL
REAL             -- Число с плавающей точкой (6 знаков)
DOUBLE PRECISION -- Число с плавающей точкой (15 знаков)
```

**Примеры:**
```sql
CREATE TABLE products (
    id INTEGER,
    price DECIMAL(10,2),  -- 99999999.99
    quantity SMALLINT
);
```

### Строковые типы:
```sql
CHAR(10)         -- Фиксированная длина (всегда 10 символов)
VARCHAR(255)     -- Переменная длина (до 255 символов)
TEXT             -- Неограниченная длина
```

**Примеры:**
```sql
CREATE TABLE users (
    name VARCHAR(50),
    description TEXT,
    code CHAR(5)  -- Всегда 5 символов
);
```

### Дата и время:
```sql
DATE             -- Только дата (2024-01-15)
TIME             -- Только время (14:30:00)
TIMESTAMP        -- Дата и время (2024-01-15 14:30:00)
TIMESTAMP WITH TIME ZONE  -- С часовым поясом
```

**Примеры:**
```sql
CREATE TABLE orders (
    order_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Логический тип:
```sql
BOOLEAN          -- TRUE, FALSE, NULL
```

**Пример:**
```sql
CREATE TABLE tasks (
    is_completed BOOLEAN DEFAULT FALSE
);
```

---

## 3. Создание таблиц (CREATE TABLE)

### Базовый синтаксис:
```sql
CREATE TABLE имя_таблицы (
    столбец1 тип_данных ограничения,
    столбец2 тип_данных ограничения,
    ...
);
```

### Пример простой таблицы:
```sql
CREATE TABLE students (
    id INTEGER,
    name VARCHAR(100),
    age INTEGER,
    email VARCHAR(255)
);
```

### Ограничения (Constraints):

#### NOT NULL — поле обязательно:
```sql
CREATE TABLE users (
    id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255)  -- Может быть NULL
);
```

#### UNIQUE — уникальное значение:
```sql
CREATE TABLE users (
    id INTEGER,
    email VARCHAR(255) UNIQUE,  -- Каждый email уникален
    username VARCHAR(50) UNIQUE
);
```

#### PRIMARY KEY — первичный ключ:
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,  -- Уникальный идентификатор
    name VARCHAR(100)
);

-- Или составной ключ:
CREATE TABLE order_items (
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    PRIMARY KEY (order_id, product_id)  -- Комбинация уникальна
);
```

#### FOREIGN KEY — внешний ключ (связь между таблицами):
```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- С опциями:
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE      -- При удалении пользователя удалить его заказы
        ON UPDATE CASCADE       -- При изменении id пользователя обновить в заказах
);
```

**Варианты ON DELETE/ON UPDATE:**
- `CASCADE` — каскадное удаление/обновление
- `SET NULL` — установить NULL
- `SET DEFAULT` — установить значение по умолчанию
- `RESTRICT` — запретить удаление/обновление
- `NO ACTION` — ничего не делать (по умолчанию)

#### CHECK — проверка условия:
```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    price DECIMAL(10,2) CHECK (price > 0),  -- Цена должна быть положительной
    age INTEGER CHECK (age >= 0 AND age <= 120),
    status VARCHAR(20) CHECK (status IN ('active', 'inactive', 'pending'))
);
```

#### DEFAULT — значение по умолчанию:
```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quantity INTEGER DEFAULT 1
);
```

### Полный пример таблицы:
```sql
CREATE TABLE employees (
    id SERIAL PRIMARY KEY,                    -- Автоинкремент
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    salary DECIMAL(10,2) CHECK (salary > 0),
    department_id INTEGER,
    hire_date DATE DEFAULT CURRENT_DATE,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (department_id) REFERENCES departments(id)
        ON DELETE SET NULL
);
```

---

## 4. Вставка данных (INSERT)

### Базовый синтаксис:
```sql
INSERT INTO имя_таблицы (столбец1, столбец2, ...)
VALUES (значение1, значение2, ...);
```

### Примеры:
```sql
-- Вставка одной строки
INSERT INTO students (name, age, email)
VALUES ('Иван Петров', 20, 'ivan@example.com');

-- Вставка нескольких строк
INSERT INTO students (name, age, email)
VALUES 
    ('Мария Сидорова', 21, 'maria@example.com'),
    ('Петр Иванов', 19, 'petr@example.com'),
    ('Анна Козлова', 22, 'anna@example.com');

-- Вставка всех столбцов (порядок важен!)
INSERT INTO students
VALUES (1, 'Иван Петров', 20, 'ivan@example.com');

-- Вставка с использованием DEFAULT
INSERT INTO orders (user_id, total)
VALUES (1, 1000.00);
-- status и created_at получат значения по умолчанию

-- Вставка из другой таблицы
INSERT INTO students_archive (name, age, email)
SELECT name, age, email
FROM students
WHERE age > 25;
```

---

## 5. Выборка данных (SELECT)

### Базовый синтаксис:
```sql
SELECT столбец1, столбец2, ...
FROM имя_таблицы
WHERE условие
ORDER BY столбец
LIMIT количество;
```

### Выбор всех столбцов:
```sql
SELECT * FROM students;
```

### Выбор конкретных столбцов:
```sql
SELECT name, age FROM students;
```

### Алиасы (псевдонимы):
```sql
SELECT 
    name AS имя_студента,
    age AS возраст,
    email AS электронная_почта
FROM students;

-- Или короткий вариант:
SELECT name имя, age возраст FROM students;
```

### WHERE — фильтрация данных:

#### Простые условия:
```sql
-- Равенство
SELECT * FROM students WHERE age = 20;

-- Неравенство
SELECT * FROM students WHERE age != 20;
SELECT * FROM students WHERE age <> 20;  -- То же самое

-- Больше, меньше
SELECT * FROM products WHERE price > 100;
SELECT * FROM products WHERE price >= 100;
SELECT * FROM products WHERE price < 50;
SELECT * FROM products WHERE price <= 50;

-- BETWEEN (включительно)
SELECT * FROM products WHERE price BETWEEN 10 AND 100;
-- Эквивалентно: price >= 10 AND price <= 100

-- IN (в списке)
SELECT * FROM students WHERE age IN (18, 19, 20);
SELECT * FROM products WHERE category IN ('Electronics', 'Books', 'Clothing');

-- NOT IN (не в списке)
SELECT * FROM students WHERE age NOT IN (18, 19, 20);

-- IS NULL / IS NOT NULL
SELECT * FROM students WHERE email IS NULL;
SELECT * FROM students WHERE email IS NOT NULL;
```

#### Логические операторы:
```sql
-- AND (И)
SELECT * FROM students WHERE age >= 18 AND age <= 25;

-- OR (ИЛИ)
SELECT * FROM students WHERE age < 18 OR age > 65;

-- NOT (НЕ)
SELECT * FROM students WHERE NOT age = 20;
SELECT * FROM students WHERE age != 20;  -- То же самое

-- Комбинации
SELECT * FROM products 
WHERE (category = 'Electronics' OR category = 'Computers')
  AND price > 100
  AND stock > 0;
```

### ORDER BY — сортировка:
```sql
-- По возрастанию (ASC по умолчанию)
SELECT * FROM students ORDER BY age;
SELECT * FROM students ORDER BY age ASC;

-- По убыванию
SELECT * FROM students ORDER BY age DESC;

-- По нескольким столбцам
SELECT * FROM students ORDER BY age DESC, name ASC;

-- По номеру столбца (не рекомендуется, но работает)
SELECT name, age, email FROM students ORDER BY 2 DESC;  -- Сортировка по age
```

### LIMIT и OFFSET — ограничение результатов:
```sql
-- Первые 10 записей
SELECT * FROM students LIMIT 10;

-- Пропустить первые 5, взять следующие 10
SELECT * FROM students LIMIT 10 OFFSET 5;

-- Топ-5 самых дорогих товаров
SELECT * FROM products ORDER BY price DESC LIMIT 5;
```

### DISTINCT — уникальные значения:
```sql
-- Уникальные возрасты
SELECT DISTINCT age FROM students;

-- Уникальные комбинации
SELECT DISTINCT category, brand FROM products;
```

---

## 6. Обновление данных (UPDATE)

### Базовый синтаксис:
```sql
UPDATE имя_таблицы
SET столбец1 = значение1, столбец2 = значение2, ...
WHERE условие;
```

### Примеры:
```sql
-- Обновить одну запись
UPDATE students 
SET age = 21 
WHERE id = 1;

-- Обновить несколько полей
UPDATE students 
SET age = 21, email = 'newemail@example.com'
WHERE id = 1;

-- Обновить все записи (ОСТОРОЖНО!)
UPDATE products SET discount = 0.1;  -- Все товары получат скидку 10%

-- Обновить с вычислением
UPDATE products 
SET price = price * 1.1  -- Увеличить цену на 10%
WHERE category = 'Electronics';

-- Обновить с использованием подзапроса
UPDATE orders 
SET total = (
    SELECT SUM(price * quantity) 
    FROM order_items 
    WHERE order_id = orders.id
);
```

**⚠️ ВАЖНО:** Всегда используйте WHERE, иначе обновятся ВСЕ строки!

---

## 7. Удаление данных (DELETE)

### Базовый синтаксис:
```sql
DELETE FROM имя_таблицы
WHERE условие;
```

### Примеры:
```sql
-- Удалить одну запись
DELETE FROM students WHERE id = 1;

-- Удалить несколько записей
DELETE FROM students WHERE age < 18;

-- Удалить все записи (ОСТОРОЖНО!)
DELETE FROM students;  -- Удалит ВСЕ строки!

-- Удалить с использованием подзапроса
DELETE FROM orders 
WHERE user_id IN (
    SELECT id FROM users WHERE status = 'inactive'
);
```

**⚠️ ВАЖНО:** 
- `DELETE` удаляет строки, но не структуру таблицы
- `TRUNCATE TABLE имя_таблицы` — быстрее удаляет все строки
- `DROP TABLE имя_таблицы` — удаляет саму таблицу

---

## 8. Агрегатные функции

### Основные функции:
```sql
COUNT(*)          -- Количество строк
COUNT(столбец)    -- Количество не-NULL значений
SUM(столбец)      -- Сумма
AVG(столбец)      -- Среднее значение
MAX(столбец)      -- Максимальное значение
MIN(столбец)      -- Минимальное значение
```

### Примеры:
```sql
-- Общее количество студентов
SELECT COUNT(*) FROM students;

-- Количество студентов с указанным email
SELECT COUNT(email) FROM students;

-- Средний возраст
SELECT AVG(age) FROM students;

-- Минимальный и максимальный возраст
SELECT MIN(age), MAX(age) FROM students;

-- Сумма всех заказов
SELECT SUM(total) FROM orders;

-- Комбинация функций
SELECT 
    COUNT(*) AS всего_студентов,
    AVG(age) AS средний_возраст,
    MIN(age) AS минимальный_возраст,
    MAX(age) AS максимальный_возраст
FROM students;
```

---

## 9. GROUP BY — группировка данных

### Синтаксис:
```sql
SELECT столбец, агрегатная_функция(столбец)
FROM таблица
GROUP BY столбец;
```

### Примеры:
```sql
-- Количество студентов каждого возраста
SELECT age, COUNT(*) AS количество
FROM students
GROUP BY age;

-- Средняя цена по категориям
SELECT category, AVG(price) AS средняя_цена
FROM products
GROUP BY category;

-- Сумма заказов по каждому пользователю
SELECT user_id, SUM(total) AS общая_сумма
FROM orders
GROUP BY user_id;

-- Группировка по нескольким столбцам
SELECT category, brand, COUNT(*) AS количество
FROM products
GROUP BY category, brand;

-- С сортировкой
SELECT category, AVG(price) AS средняя_цена
FROM products
GROUP BY category
ORDER BY средняя_цена DESC;
```

### HAVING — фильтрация групп:

**Разница между WHERE и HAVING:**
- `WHERE` фильтрует строки ДО группировки
- `HAVING` фильтрует группы ПОСЛЕ группировки

```sql
-- Категории с более чем 10 товарами
SELECT category, COUNT(*) AS количество
FROM products
GROUP BY category
HAVING COUNT(*) > 10;

-- Пользователи с общей суммой заказов больше 1000
SELECT user_id, SUM(total) AS общая_сумма
FROM orders
GROUP BY user_id
HAVING SUM(total) > 1000;

-- Комбинация WHERE и HAVING
SELECT category, AVG(price) AS средняя_цена
FROM products
WHERE price > 10              -- Фильтр строк ДО группировки
GROUP BY category
HAVING AVG(price) > 50        -- Фильтр групп ПОСЛЕ группировки
ORDER BY средняя_цена DESC;
```

---

## 10. Подзапросы (Subqueries)

### Подзапрос в WHERE:
```sql
-- Студенты старше среднего возраста
SELECT * FROM students
WHERE age > (SELECT AVG(age) FROM students);

-- Товары дороже среднего в своей категории
SELECT * FROM products p1
WHERE price > (
    SELECT AVG(price) 
    FROM products p2 
    WHERE p2.category = p1.category
);
```

### Подзапрос с IN:
```sql
-- Заказы пользователей из Москвы
SELECT * FROM orders
WHERE user_id IN (
    SELECT id FROM users WHERE city = 'Москва'
);
```

### Подзапрос с EXISTS:
```sql
-- Пользователи, у которых есть заказы
SELECT * FROM users u
WHERE EXISTS (
    SELECT 1 FROM orders o WHERE o.user_id = u.id
);

-- Пользователи без заказов
SELECT * FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.user_id = u.id
);
```

### Подзапрос в SELECT:
```sql
-- Список заказов с именем пользователя
SELECT 
    o.id,
    o.total,
    (SELECT name FROM users WHERE id = o.user_id) AS имя_пользователя
FROM orders o;
```

### Подзапрос в FROM (производная таблица):
```sql
-- Средняя цена по категориям, где средняя цена > 100
SELECT category, средняя_цена
FROM (
    SELECT category, AVG(price) AS средняя_цена
    FROM products
    GROUP BY category
) AS категории_цены
WHERE средняя_цена > 100;
```

---

## 11. JOIN — соединение таблиц

### INNER JOIN (внутреннее соединение):
Возвращает только совпадающие строки из обеих таблиц.

```sql
SELECT столбцы
FROM таблица1
INNER JOIN таблица2 ON таблица1.столбец = таблица2.столбец;
```

**Пример:**
```sql
-- Заказы с информацией о пользователях
SELECT o.id, o.total, u.name, u.email
FROM orders o
INNER JOIN users u ON o.user_id = u.id;

-- С несколькими JOIN
SELECT o.id, o.total, u.name, p.name AS продукт
FROM orders o
INNER JOIN users u ON o.user_id = u.id
INNER JOIN order_items oi ON o.id = oi.order_id
INNER JOIN products p ON oi.product_id = p.id;
```

### LEFT JOIN (левое внешнее соединение):
Возвращает все строки из левой таблицы и совпадающие из правой.

```sql
-- Все пользователи и их заказы (если есть)
SELECT u.name, o.id AS order_id, o.total
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;

-- Пользователи без заказов
SELECT u.name
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE o.id IS NULL;
```

### RIGHT JOIN (правое внешнее соединение):
Возвращает все строки из правой таблицы и совпадающие из левой.

```sql
-- Все заказы и информация о пользователях
SELECT o.id, o.total, u.name
FROM orders o
RIGHT JOIN users u ON o.user_id = u.id;
```

### FULL OUTER JOIN (полное внешнее соединение):
Возвращает все строки из обеих таблиц.

```sql
SELECT u.name, o.id AS order_id
FROM users u
FULL OUTER JOIN orders o ON u.id = o.user_id;
```

### CROSS JOIN (декартово произведение):
Каждая строка первой таблицы соединяется с каждой строкой второй.

```sql
-- Все комбинации размеров и цветов
SELECT s.size, c.color
FROM sizes s
CROSS JOIN colors c;
```

### Сравнение JOIN:

| Тип JOIN | Описание | Пример использования |
|----------|----------|----------------------|
| INNER JOIN | Только совпадения | Заказы с пользователями |
| LEFT JOIN | Все слева + совпадения справа | Все пользователи и их заказы |
| RIGHT JOIN | Все справа + совпадения слева | Все заказы и пользователи |
| FULL JOIN | Все из обеих таблиц | Полная информация |
| CROSS JOIN | Все комбинации | Генерация комбинаций |

---

## 12. Функции работы со строками

### Основные функции:
```sql
-- Длина строки
SELECT LENGTH('Hello');  -- 5
SELECT CHAR_LENGTH('Привет');  -- 6

-- Верхний/нижний регистр
SELECT UPPER('hello');  -- 'HELLO'
SELECT LOWER('HELLO');  -- 'hello'

-- Объединение строк
SELECT CONCAT('Hello', ' ', 'World');  -- 'Hello World'
SELECT 'Hello' || ' ' || 'World';  -- 'Hello World' (PostgreSQL)

-- Подстрока
SELECT SUBSTRING('Hello World', 1, 5);  -- 'Hello'
SELECT SUBSTRING('Hello World' FROM 1 FOR 5);  -- 'Hello'

-- Поиск позиции
SELECT POSITION('World' IN 'Hello World');  -- 7

-- Замена
SELECT REPLACE('Hello World', 'World', 'SQL');  -- 'Hello SQL'

-- Обрезка пробелов
SELECT TRIM('  Hello  ');  -- 'Hello'
SELECT LTRIM('  Hello');  -- 'Hello' (слева)
SELECT RTRIM('Hello  ');  -- 'Hello' (справа)

-- Дополнение строки
SELECT LPAD('5', 3, '0');  -- '005' (дополнить слева нулями до 3 символов)
SELECT RPAD('5', 3, '0');  -- '500' (дополнить справа)

-- Извлечение части
SELECT LEFT('Hello', 3);  -- 'Hel'
SELECT RIGHT('Hello', 3);  -- 'llo'
```

### Примеры использования:
```sql
-- Форматирование имени
SELECT 
    UPPER(first_name) || ' ' || UPPER(last_name) AS полное_имя
FROM users;

-- Поиск по части строки
SELECT * FROM products 
WHERE name LIKE '%phone%';

-- Извлечение домена из email
SELECT 
    email,
    SUBSTRING(email FROM POSITION('@' IN email) + 1) AS домен
FROM users;
```

---

## 13. Функции работы с датами

### Основные функции:
```sql
-- Текущая дата и время
SELECT CURRENT_DATE;        -- 2024-01-15
SELECT CURRENT_TIME;        -- 14:30:00
SELECT CURRENT_TIMESTAMP;   -- 2024-01-15 14:30:00
SELECT NOW();               -- Текущая дата и время

-- Извлечение частей даты
SELECT EXTRACT(YEAR FROM CURRENT_DATE);     -- 2024
SELECT EXTRACT(MONTH FROM CURRENT_DATE);    -- 1
SELECT EXTRACT(DAY FROM CURRENT_DATE);     -- 15

-- Форматирование даты (зависит от СУБД)
SELECT DATE_FORMAT(CURRENT_DATE, '%Y-%m-%d');  -- MySQL
SELECT TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD');     -- PostgreSQL

-- Арифметика с датами
SELECT CURRENT_DATE + INTERVAL '1 day';    -- Завтра
SELECT CURRENT_DATE - INTERVAL '1 month';   -- Месяц назад
SELECT CURRENT_DATE + 7;                    -- Через неделю (PostgreSQL)

-- Разница между датами
SELECT CURRENT_DATE - '2024-01-01';        -- Количество дней (PostgreSQL)
SELECT DATEDIFF('2024-01-15', '2024-01-01');  -- MySQL
```

### Примеры:
```sql
-- Заказы за последние 30 дней
SELECT * FROM orders
WHERE order_date >= CURRENT_DATE - INTERVAL '30 days';

-- Возраст пользователей
SELECT 
    name,
    EXTRACT(YEAR FROM AGE(birth_date)) AS возраст
FROM users;

-- Группировка по месяцам
SELECT 
    EXTRACT(YEAR FROM order_date) AS год,
    EXTRACT(MONTH FROM order_date) AS месяц,
    COUNT(*) AS количество_заказов
FROM orders
GROUP BY год, месяц
ORDER BY год, месяц;
```

---

## 14. Условные выражения

### CASE — условная логика:
```sql
-- Простой CASE
SELECT 
    name,
    CASE category
        WHEN 'Electronics' THEN 'Электроника'
        WHEN 'Books' THEN 'Книги'
        ELSE 'Другое'
    END AS категория_рус
FROM products;

-- Поисковый CASE
SELECT 
    name,
    price,
    CASE
        WHEN price < 10 THEN 'Дешевый'
        WHEN price < 50 THEN 'Средний'
        WHEN price < 100 THEN 'Дорогой'
        ELSE 'Очень дорогой'
    END AS ценовая_категория
FROM products;

-- CASE в агрегатных функциях
SELECT 
    COUNT(CASE WHEN status = 'active' THEN 1 END) AS активных,
    COUNT(CASE WHEN status = 'inactive' THEN 1 END) AS неактивных
FROM users;
```

### COALESCE — первое не-NULL значение:
```sql
SELECT COALESCE(NULL, NULL, 'Значение', NULL);  -- 'Значение'
SELECT COALESCE(phone, email, 'Не указано') AS контакт FROM users;
```

### NULLIF — возвращает NULL если значения равны:
```sql
SELECT NULLIF(5, 5);  -- NULL
SELECT NULLIF(5, 3);  -- 5
```

---

## 15. Изменение структуры таблиц (ALTER TABLE)

### Добавление столбца:
```sql
ALTER TABLE students ADD COLUMN phone VARCHAR(20);
ALTER TABLE students ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
```

### Удаление столбца:
```sql
ALTER TABLE students DROP COLUMN phone;
```

### Изменение типа столбца:
```sql
ALTER TABLE students ALTER COLUMN age TYPE INTEGER;
```

### Переименование столбца:
```sql
ALTER TABLE students RENAME COLUMN age TO возраст;
```

### Переименование таблицы:
```sql
ALTER TABLE students RENAME TO ученики;
```

### Добавление ограничения:
```sql
-- NOT NULL
ALTER TABLE students ALTER COLUMN email SET NOT NULL;

-- UNIQUE
ALTER TABLE students ADD CONSTRAINT unique_email UNIQUE(email);

-- CHECK
ALTER TABLE students ADD CONSTRAINT check_age CHECK (age >= 0 AND age <= 120);

-- FOREIGN KEY
ALTER TABLE orders ADD CONSTRAINT fk_user 
    FOREIGN KEY (user_id) REFERENCES users(id);
```

### Удаление ограничения:
```sql
ALTER TABLE students DROP CONSTRAINT unique_email;
ALTER TABLE students DROP CONSTRAINT check_age;
```

---

## 16. Удаление таблиц и данных

### Удаление всех данных (структура остается):
```sql
DELETE FROM students;  -- Медленно, можно откатить
TRUNCATE TABLE students;  -- Быстро, нельзя откатить
```

### Удаление таблицы:
```sql
DROP TABLE students;  -- Удаляет таблицу полностью
DROP TABLE IF EXISTS students;  -- Безопасный вариант
```

### Удаление базы данных:
```sql
DROP DATABASE mydb;
```

---

## 17. Индексы

Индексы ускоряют поиск данных, но замедляют вставку/обновление.

### Создание индекса:
```sql
-- Простой индекс
CREATE INDEX idx_email ON users(email);

-- Уникальный индекс
CREATE UNIQUE INDEX idx_unique_email ON users(email);

-- Составной индекс
CREATE INDEX idx_name_age ON users(last_name, first_name);

-- Частичный индекс (только для определенных строк)
CREATE INDEX idx_active_users ON users(email) WHERE status = 'active';
```

### Удаление индекса:
```sql
DROP INDEX idx_email;
```

---

## 18. Представления (Views)

Представление — виртуальная таблица на основе запроса.

### Создание представления:
```sql
CREATE VIEW active_users AS
SELECT id, name, email
FROM users
WHERE status = 'active';

-- Использование
SELECT * FROM active_users;
```

### Обновляемое представление:
```sql
CREATE VIEW user_orders AS
SELECT u.id, u.name, o.id AS order_id, o.total
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;
```

### Удаление представления:
```sql
DROP VIEW active_users;
```

---

## 19. Транзакции

Транзакция — группа операций, выполняемых как единое целое.

### Базовые команды:
```sql
BEGIN;           -- Начать транзакцию
COMMIT;          -- Сохранить изменения
ROLLBACK;        -- Откатить изменения
```

### Пример:
```sql
BEGIN;

INSERT INTO orders (user_id, total) VALUES (1, 100.00);
UPDATE users SET balance = balance - 100 WHERE id = 1;

-- Если все ОК:
COMMIT;

-- Если ошибка:
ROLLBACK;
```

### ACID свойства:
- **Atomicity (Атомарность)** — все или ничего
- **Consistency (Согласованность)** — данные всегда валидны
- **Isolation (Изоляция)** — транзакции не мешают друг другу
- **Durability (Долговечность)** — изменения сохраняются

---

---

## ЧАСТЬ 2: POSTGRESQL - СПЕЦИФИКА

---

## 20. Особенности PostgreSQL

PostgreSQL — мощная объектно-реляционная СУБД с расширенными возможностями.

### Основные отличия от стандартного SQL:

1. **Расширенные типы данных**
2. **Массивы**
3. **JSON поддержка**
4. **Полнотекстовый поиск**
5. **Расширяемость**

---

## 21. Типы данных PostgreSQL

### Специфичные типы:

#### SERIAL (автоинкремент):
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,  -- Автоматически увеличивается
    name VARCHAR(100)
);
-- Эквивалентно: INTEGER с DEFAULT nextval('sequence_name')
```

Варианты:
- `SERIAL` — INTEGER (1 до 2,147,483,647)
- `BIGSERIAL` — BIGINT
- `SMALLSERIAL` — SMALLINT

#### Массивы:
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    tags TEXT[],  -- Массив строк
    prices INTEGER[]  -- Массив чисел
);

-- Вставка
INSERT INTO products (name, tags, prices)
VALUES ('Phone', ARRAY['electronics', 'mobile'], ARRAY[100, 200, 300]);

-- Запросы
SELECT * FROM products WHERE 'electronics' = ANY(tags);
SELECT name, tags[1] AS первый_тег FROM products;  -- Первый элемент массива
```

#### JSON и JSONB:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    metadata JSONB  -- JSONB быстрее для запросов
);

-- Вставка
INSERT INTO users (name, metadata)
VALUES ('John', '{"age": 30, "city": "Moscow", "hobbies": ["reading", "coding"]}');

-- Запросы
SELECT * FROM users WHERE metadata->>'city' = 'Moscow';
SELECT name, metadata->'age' AS возраст FROM users;
SELECT name FROM users WHERE metadata @> '{"city": "Moscow"}';
```

#### UUID:
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    total DECIMAL(10,2)
);
```

#### ENUM (перечисляемый тип):
```sql
-- Создание типа
CREATE TYPE order_status AS ENUM ('pending', 'processing', 'completed', 'cancelled');

-- Использование
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    status order_status DEFAULT 'pending'
);

-- Вставка
INSERT INTO orders (status) VALUES ('pending');
```

#### Геометрические типы:
```sql
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    point POINT,
    line LINE,
    polygon POLYGON
);
```

---

## 22. Схемы (Schemas) в PostgreSQL

Схема — пространство имен для объектов БД.

### Работа со схемами:
```sql
-- Создание схемы
CREATE SCHEMA myschema;

-- Создание таблицы в схеме
CREATE TABLE myschema.users (id SERIAL, name VARCHAR(100));

-- Обращение к таблице
SELECT * FROM myschema.users;

-- Установка схемы по умолчанию
SET search_path TO myschema, public;

-- Теперь можно без префикса
SELECT * FROM users;  -- Ищет в myschema, потом в public

-- Удаление схемы
DROP SCHEMA myschema CASCADE;  -- CASCADE удалит все объекты
```

### Стандартные схемы:
- `public` — схема по умолчанию
- `information_schema` — метаданные БД
- `pg_catalog` — системные таблицы PostgreSQL

---

## 23. Расширенные возможности SELECT

### LIMIT и OFFSET:
```sql
-- Пагинация
SELECT * FROM products 
ORDER BY id 
LIMIT 10 OFFSET 20;  -- Пропустить 20, взять 10
```

### DISTINCT ON (только PostgreSQL):
```sql
-- Первая запись для каждой категории
SELECT DISTINCT ON (category) *
FROM products
ORDER BY category, price DESC;
```

### WITH (CTE - Common Table Expressions):
```sql
-- Временное представление
WITH expensive_products AS (
    SELECT * FROM products WHERE price > 100
),
active_users AS (
    SELECT * FROM users WHERE status = 'active'
)
SELECT * FROM expensive_products
UNION
SELECT * FROM active_users;

-- Рекурсивные CTE
WITH RECURSIVE numbers AS (
    SELECT 1 AS n
    UNION ALL
    SELECT n + 1 FROM numbers WHERE n < 10
)
SELECT * FROM numbers;  -- 1, 2, 3, ..., 10
```

---

## 24. Функции PostgreSQL

### Строковые функции:
```sql
-- Дополнительные функции
SELECT INITCAP('hello world');  -- 'Hello World'
SELECT SPLIT_PART('a,b,c', ',', 2);  -- 'b'
SELECT STRING_AGG(name, ', ') FROM users;  -- Объединение всех имен
```

### Математические функции:
```sql
SELECT ROUND(3.14159, 2);  -- 3.14
SELECT FLOOR(3.7);  -- 3
SELECT CEIL(3.2);  -- 4
SELECT ABS(-5);  -- 5
SELECT POWER(2, 3);  -- 8
SELECT SQRT(16);  -- 4
SELECT RANDOM();  -- Случайное число 0-1
```

### Функции даты и времени:
```sql
-- Текущее время
SELECT NOW();
SELECT CURRENT_DATE;
SELECT CURRENT_TIME;

-- Извлечение частей
SELECT EXTRACT(YEAR FROM NOW());
SELECT DATE_PART('year', NOW());  -- То же самое

-- Арифметика
SELECT NOW() + INTERVAL '1 day';
SELECT NOW() - INTERVAL '2 hours';
SELECT NOW() + '1 month'::INTERVAL;

-- Форматирование
SELECT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS');
SELECT TO_DATE('2024-01-15', 'YYYY-MM-DD');

-- Возраст
SELECT AGE('2024-01-15', '2000-01-01');  -- Интервал между датами
```

### Агрегатные функции:
```sql
-- Стандартные
SELECT COUNT(*), SUM(price), AVG(price), MAX(price), MIN(price) FROM products;

-- Дополнительные
SELECT ARRAY_AGG(name) FROM users;  -- Массив всех имен
SELECT STRING_AGG(name, ', ') FROM users;  -- Строка через запятую
SELECT JSON_AGG(json_build_object('id', id, 'name', name)) FROM users;
```

---

## 25. Оконные функции (Window Functions)

Оконные функции выполняют вычисления над набором строк, связанных с текущей строкой.

### Базовый синтаксис:
```sql
SELECT 
    столбец,
    функция() OVER (PARTITION BY ... ORDER BY ...)
FROM таблица;
```

### Примеры:
```sql
-- Нумерация строк
SELECT 
    name,
    price,
    ROW_NUMBER() OVER (ORDER BY price DESC) AS номер
FROM products;

-- Ранжирование
SELECT 
    name,
    price,
    RANK() OVER (ORDER BY price DESC) AS ранг,  -- Пропускает номера при равенстве
    DENSE_RANK() OVER (ORDER BY price DESC) AS плотный_ранг  -- Не пропускает
FROM products;

-- Сумма нарастающим итогом
SELECT 
    date,
    amount,
    SUM(amount) OVER (ORDER BY date) AS нарастающий_итог
FROM transactions;

-- Среднее по группам
SELECT 
    category,
    name,
    price,
    AVG(price) OVER (PARTITION BY category) AS средняя_цена_в_категории
FROM products;

-- Сравнение с предыдущей/следующей строкой
SELECT 
    date,
    amount,
    LAG(amount) OVER (ORDER BY date) AS предыдущая,
    LEAD(amount) OVER (ORDER BY date) AS следующая
FROM transactions;
```

---

## 26. Полнотекстовый поиск

PostgreSQL поддерживает мощный полнотекстовый поиск.

### Создание индекса:
```sql
-- Добавление столбца для поиска
ALTER TABLE products ADD COLUMN search_vector tsvector;

-- Заполнение
UPDATE products 
SET search_vector = to_tsvector('russian', name || ' ' || description);

-- Создание индекса
CREATE INDEX idx_search ON products USING GIN(search_vector);
```

### Поиск:
```sql
-- Простой поиск
SELECT * FROM products 
WHERE search_vector @@ to_tsquery('russian', 'телефон');

-- Ранжирование результатов
SELECT 
    name,
    ts_rank(search_vector, to_tsquery('russian', 'телефон')) AS релевантность
FROM products
WHERE search_vector @@ to_tsquery('russian', 'телефон')
ORDER BY релевантность DESC;
```

---

## 27. Расширения (Extensions)

PostgreSQL можно расширять дополнительными функциями.

### Популярные расширения:
```sql
-- UUID генерация
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Дополнительные функции
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Триграммы для поиска
CREATE EXTENSION IF NOT EXISTS "hstore";    -- Хранилище ключ-значение

-- Просмотр установленных расширений
SELECT * FROM pg_extension;
```

---

## 28. Управление пользователями и правами

### Создание пользователя:
```sql
CREATE USER myuser WITH PASSWORD 'mypassword';
CREATE ROLE myrole WITH LOGIN PASSWORD 'mypassword';
```

### Выдача прав:
```sql
-- Права на таблицу
GRANT SELECT, INSERT, UPDATE ON TABLE users TO myuser;
GRANT ALL PRIVILEGES ON TABLE users TO myuser;

-- Права на схему
GRANT USAGE ON SCHEMA myschema TO myuser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA myschema TO myuser;

-- Отзыв прав
REVOKE INSERT ON TABLE users FROM myuser;
```

---

## 29. Резервное копирование

### pg_dump (командная строка):
```bash
# Дамп базы данных
pg_dump -U postgres -d mydb > backup.sql

# Восстановление
psql -U postgres -d mydb < backup.sql

# Только структура
pg_dump -U postgres -d mydb --schema-only > schema.sql

# Только данные
pg_dump -U postgres -d mydb --data-only > data.sql
```

---

## 30. Полезные запросы для администрирования

### Информация о таблицах:
```sql
-- Список всех таблиц
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';

-- Столбцы таблицы
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users';

-- Размер таблицы
SELECT pg_size_pretty(pg_total_relation_size('users')) AS размер;

-- Индексы таблицы
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'users';
```

### Производительность:
```sql
-- Медленные запросы (требует настройки)
SELECT * FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;

-- Статистика по таблицам
SELECT * FROM pg_stat_user_tables;
```

---

## 31. Лучшие практики PostgreSQL

### 1. Всегда используйте параметризованные запросы:
```python
# ПЛОХО (уязвимо к SQL-инъекциям)
query = f"SELECT * FROM users WHERE name = '{name}'"

# ХОРОШО
query = "SELECT * FROM users WHERE name = %s"
cursor.execute(query, (name,))
```

### 2. Используйте транзакции:
```sql
BEGIN;
-- операции
COMMIT;  -- или ROLLBACK при ошибке
```

### 3. Создавайте индексы для часто используемых столбцов:
```sql
CREATE INDEX idx_email ON users(email);
```

### 4. Используйте правильные типы данных:
- `VARCHAR(n)` для строк известной максимальной длины
- `TEXT` для длинных текстов
- `INTEGER` vs `BIGINT` в зависимости от диапазона

### 5. Нормализация данных:
- Избегайте дублирования
- Используйте внешние ключи
- Разделяйте данные на логические таблицы

### 6. Регулярное обслуживание:
```sql
-- Анализ таблиц (обновление статистики)
ANALYZE users;

-- Пересборка индексов
REINDEX TABLE users;

-- Очистка
VACUUM ANALYZE users;
```

---

## 32. Частые ошибки и как их избежать

### 1. Забыли WHERE в UPDATE/DELETE:
```sql
-- ОПАСНО! Обновит все строки
UPDATE users SET status = 'inactive';

-- ПРАВИЛЬНО
UPDATE users SET status = 'inactive' WHERE id = 1;
```

### 2. Использование функций в WHERE:
```sql
-- МЕДЛЕННО (не может использовать индекс)
SELECT * FROM users WHERE UPPER(name) = 'JOHN';

-- БЫСТРЕЕ (может использовать индекс)
SELECT * FROM users WHERE name = 'John';
-- Или создайте функциональный индекс:
CREATE INDEX idx_upper_name ON users(UPPER(name));
```

### 3. SELECT * вместо конкретных столбцов:
```sql
-- МЕДЛЕННЕЕ
SELECT * FROM users;

-- БЫСТРЕЕ (если нужны не все столбцы)
SELECT id, name FROM users;
```

### 4. Игнорирование NULL:
```sql
-- НЕПРАВИЛЬНО (не найдет NULL)
SELECT * FROM users WHERE email = NULL;

-- ПРАВИЛЬНО
SELECT * FROM users WHERE email IS NULL;
```

---

## Заключение

Этот конспект покрывает основные концепции SQL и специфику PostgreSQL. 

**Ключевые моменты для запоминания:**
1. SQL — декларативный язык (описываете ЧТО нужно, а не КАК)
2. Всегда используйте параметризованные запросы
3. Понимайте разницу между JOIN типами
4. Используйте транзакции для целостности данных
5. Индексы ускоряют чтение, но замедляют запись
6. PostgreSQL — мощная СУБД с множеством расширенных возможностей

**Практика — лучший способ изучения!** 🚀

