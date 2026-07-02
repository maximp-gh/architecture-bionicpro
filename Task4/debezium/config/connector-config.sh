#!/bin/bash

# Ожидание доступности Kafka Connect
echo "Waiting for debezium-kafka connect to be ready..."
until curl -s -f http://debezium-kafka:8083/connectors; do
    sleep 5
done

echo "Kafka Connect is ready!"

# Удаление существующего коннектора (если есть)
echo "Removing existing connector if present..."
curl -X DELETE http://debezium-kafka:8083/connectors/postgres-crm-connector || true

# Регистрация коннектора
echo "Registering Debezium connector..."
curl -X POST \
     -H "Content-Type: application/json" \
     --data @/etc/debezium/config/postgresы-connector.json \
     http://debezium-kafka:8083/connectors

# Проверка статуса
echo -e "\n Connector status:"
curl -s http://debezium-kafka:8083/connectors/postgres-crm-connector/status | jq '.'

# Список всех коннекторов
echo -e "\n All connectors:"
curl -s http://debezium-kafka:8083/connectors | jq '.'