#!/bin/bash

echo "========================================="
echo "1. Проверка Postgres"
echo "========================================="
docker exec crm_db psql -U crm_user -d crm_db -c "SELECT COUNT(*) FROM crm.customers;"

echo -e "\n========================================="
echo "2. Проверка Kafka топиков"
echo "========================================="
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list | grep customers

echo -e "\n========================================="
echo "3. Проверка данных в Kafka"
echo "========================================="
docker exec kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic crm.crm.customers --from-beginning --max-messages 1 --timeout-ms 2000

echo -e "\n========================================="
echo "3. Проверка данных в Clickhouse"
echo "========================================="
# 1. Данные в витрине
docker exec clickhouse clickhouse-client --query "SELECT COUNT(*) FROM reports_db.customers_mv;"

# 2. Вывод последних записей
docker exec clickhouse clickhouse-client --query "SELECT * FROM reports_db.customers_mv ORDER BY id DESC LIMIT 5;"
