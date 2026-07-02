-- Создание схемы CRM
CREATE SCHEMA IF NOT EXISTS crm;

CREATE TABLE IF NOT EXISTS crm.customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    age NUMERIC,
    gender VARCHAR(10),
    country VARCHAR(100),
    address VARCHAR(255),
    phone VARCHAR(25)
);

-- Устанавливаем поиск по схеме crm
-- SET search_path TO crm, public;

COPY crm.customers(id, name, email, age, gender, country, address, phone)
FROM '/docker-entrypoint-initdb.d/crm.csv'
DELIMITER ','
CSV HEADER;

SELECT setval('crm.customers_id_seq', COALESCE((SELECT MAX(id) FROM crm.customers), 0) + 1, false);

-- Создание публикации для Debezium - включает CDC
CREATE PUBLICATION crm_publication FOR TABLE crm.customers;