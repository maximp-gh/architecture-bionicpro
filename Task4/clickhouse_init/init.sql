-- Создание базы данных
CREATE DATABASE IF NOT EXISTS reports_db;

USE reports_db;

-- ========================================
-- 1. Таблица-очередь для приёма данных из Kafka
-- ========================================
CREATE TABLE IF NOT EXISTS customers_queue
(
    raw String
)
ENGINE = Kafka()
SETTINGS
    kafka_broker_list = 'kafka:9092',          -- имя сервиса Kafka в docker-compose
    kafka_topic_list = 'crm.crm.customers',    -- топик от Debezium
    kafka_group_name = 'clickhouse_customers', -- обязательный параметр (определяет получателя)
    kafka_format = 'JSONAsString';             -- берём value как строку JSON
    --kafka_auto_offset_reset = 'earliest';    -- читать с начала топика (для отладки)

-- ========================================
-- 2. Витрина (целевая таблица)
-- ========================================
CREATE TABLE customers (
    id UInt64,
    name String,
    email String,
    age Int32,
    gender String,
    country String,
    address String,
    phone String,
    event_time DateTime,       -- время на базе информации от Кафка
    _op String,                -- операция от debezium: c/u/d от Debezium
    _offset Int64,
    _partition Int32
) ENGINE = MergeTree()
ORDER BY (id);

-- ========================================
-- 3. Materialized View для автоматической загрузки
-- ========================================

CREATE MATERIALIZED VIEW customers_mv TO customers AS
SELECT
    -- Плоские поля, без 'after'
    toUInt64OrZero(JSONExtractRaw(raw, 'id')) AS id,
    JSONExtractString(raw, 'name') AS name,
    JSONExtractString(raw, 'email') AS email,
    
    -- age приходит как float (55.0)
    toFloat64OrZero(JSONExtractRaw(raw, 'age')) AS age,
    
    JSONExtractString(raw, 'gender') AS gender,
    JSONExtractString(raw, 'country') AS country,
    JSONExtractString(raw, 'address') AS address,
    JSONExtractString(raw, 'phone') AS phone,
    
    -- Правильное имя поля времени от Debezium
    toDateTime(toInt64OrZero(JSONExtractRaw(raw, '__source_ts_ms')) / 1000) AS event_time,
    
    -- Правильное имя операции (__op)
    JSONExtractString(raw, '__op') AS _op    
FROM customers_queue;

-- ========================================
-- 4. Проверка (без SELECT из очереди)
-- ========================================

SELECT '✅ ClickHouse initialized!' AS status;

-- Проверяем данные в витрине (не в очереди)
SELECT 'customers' AS source, COUNT(*) AS records FROM customers;

-- Проверяем статус Kafka потребителя
-- Посмотреть все колонки
DESCRIBE system.kafka_consumers;
-- Или просто SELECT *
SELECT * FROM system.kafka_consumers LIMIT 1;


