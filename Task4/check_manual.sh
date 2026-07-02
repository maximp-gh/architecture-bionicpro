# 1. Добавить нового клиента в Postgres
docker exec -it crm_db psql -U crm_user -d crm_db '
INSERT INTO crm.customers (name, email, age, gender, country, address, phone) VALUES ('Test User', 'test@example.com', 25, 'Male', 'USA', 'Test Address', '+1234567899');

# 2. Проверить топик Kafka
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic crm.crm.customers --from-beginning

# 3. Проверить ClickHouse
docker exec clickhouse clickhouse-client --query "SELECT * FROM reports_db.customers_mv WHERE email='test@example.com';"