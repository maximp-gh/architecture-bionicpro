# Sprint9

## Задание 1

Все поднимаемые сервисы (keycloak, ldap, etc) описаны в docker-compose.yaml

### Диаграмма

BionicPRO_C4_model.drawio.xml

### PKCE

Чтобы реализоваmь PKCE (Proof Key for Code Exchange), 
- конфигурируем KeyCloak
- добавляем в react взаимодействие с KeyCloak параметр

```
pkceMethod: 'S256'
```
См. код в папке **frontend_pkce**

### Backend

См. **bionicpro-auth**

### Frontend с сессией

См. **frontend**

### Манипуляции с Keycloak включая Oauth от Яндекс ID

keycloak-results-export.json


## Задание 2


### Диаграмма архитектуры.

Task2/Airflow_C4_model.drawio.xml

### Код в репозитории, связанный с Airflow в отдельную папку.

См. Task2:
dags и
docker-compose.yaml

Коннекшен к postgres ("write_to_postgres") необходимо настраивать в airflow UI.

### Имплементация API для фактического сбора данных из ClickHouse.

frontend_reports
reports

docker-compose.yaml


## Задание 3

1. Код схемы взаимодействия с S3 и CDN добавлен тут:

reports:
- reports_service.py
- s3.py

2. Изменен docker-compose.yaml:

Добавлены сервисы minio и nginx (для CDN).
Файл конфигурации Nginx с настройками reverse proxy тут:

Task3/nginx.conf


## Задание 4

См. папку **Task4**.

1. Файл конфигурации развёртывания Kafka и kafka-connect в docker compose: 
*docker-compose-debezium.yaml*

2. Файл конфигурации debezium-connector захвата данных из БД CRM:

*debezium/config/postgress-connector.json*

Также см. сервис регистрации коннектора в kafka: *connect-init* в compose

3. Cкрипты приёма данных через механизм KafkaEngine и код создания MaterializedView для витрины в Clickhouse

*clickhouse_init/init.sql*


Проверку, что все срослось, можно провести при помощи *check.sh* или UI (добавлены в compose - для kafka и clickhouse).




