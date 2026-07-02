from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.operators.postgres_operator import PostgresOperator
from datetime import datetime, timedelta
import csv
from airflow.models import Variable
import os

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2026, 6, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'prosthesis_telemetry_etl',
    default_args=default_args,
    description='ETL телеметрии протезов',
    schedule_interval='0 1 * * *',
    catchup=False
)

def load_telemetry_from_csv(**context):
    """Загружает данные телеметрии из csv во временную таблицу"""
    telemetry_path = 'sample_files/olap.csv'
    telemetry_data = []
    
    with open(telemetry_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {
                'user_id': int(row['user_id']),
                'prosthesis_type': row['prosthesis_type'],
                'muscle_group': row['muscle_group'],
                'signal_frequency': float(row['signal_frequency']),
                'signal_duration': float(row['signal_duration']),
                'signal_amplitude': float(row['signal_amplitude']),
                'signal_time': row['signal_time']
            }
            telemetry_data.append(record)
    
    context['task_instance'].xcom_push(key='telemetry_data', value=telemetry_data)
    print(f"Загружено записей телеметрии: {len(telemetry_data)}")
    return len(telemetry_data)

def load_users_from_csv(**context):
    """Загружает данные пользователей из CSV во временную таблицу"""
    users_path = 'sample_files/crm.csv'
    users_data = []
    
    with open(users_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            users_data.append({
                'user_id': int(row['id']),
                'name': row['name'],
                'email': row['email'],
                'age': int(row['age']) if row['age'] else 0,
                'gender': row['gender'],
                'country': row['country'],
                'address': row['address'],
                'phone': row['phone']
            })
    
    context['task_instance'].xcom_push(key='users_data', value=users_data)
    print(f"Загружено пользователей: {len(users_data)}")
    return len(users_data)

# Создаем временные таблицы и загружаем данные через PostgresOperator
create_temp_tables = PostgresOperator(
    task_id='create_temp_tables',
    postgres_conn_id='write_to_postgres',
    sql="""
        DROP TABLE IF EXISTS temp_telemetry;
        CREATE TABLE temp_telemetry (
            user_id INTEGER,
            prosthesis_type VARCHAR(100),
            muscle_group VARCHAR(100),
            signal_frequency FLOAT,
            signal_duration FLOAT,
            signal_amplitude FLOAT,
            signal_time TIMESTAMP
        );
        
        DROP TABLE IF EXISTS temp_users;
        CREATE TABLE temp_users (
            user_id INTEGER,
            name VARCHAR(200),
            email VARCHAR(200),
            age INTEGER,
            gender VARCHAR(50),
            country VARCHAR(100),
            address TEXT,
            phone VARCHAR(50)
        );
    """,
    dag=dag
)

# Task для загрузки данных через Python (можно заменить на CopyOperator если файлы на сервере)
# Оставляем PythonOperator для загрузки данных в XCom, затем вставляем через PostgresHook

start = DummyOperator(task_id='start', dag=dag)

load_telemetry_task = PythonOperator(
    task_id='load_telemetry_task',
    python_callable=load_telemetry_from_csv,
    dag=dag
)

load_users_task = PythonOperator(
    task_id='load_users_task',
    python_callable=load_users_from_csv,
    dag=dag
)


# Создаем основную таблицу
create_facts_table = PostgresOperator(
    task_id='create_facts_table',
    postgres_conn_id='write_to_postgres',
    sql="""
        DROP TABLE IF EXISTS prosthesis_sensor_facts;
        CREATE TABLE IF NOT EXISTS prosthesis_sensor_facts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            prosthesis_type VARCHAR(100),
            muscle_group VARCHAR(100),
            signal_frequency FLOAT,
            signal_duration FLOAT,
            signal_amplitude FLOAT,
            signal_time TIMESTAMP,
            user_name VARCHAR(200),
            user_email VARCHAR(200),
            user_age INTEGER,
            user_gender VARCHAR(50),
            user_country VARCHAR(100),
            user_address TEXT,
            user_phone VARCHAR(50),
            load_date DATE,
            year VARCHAR(4),
            month VARCHAR(2),
            day VARCHAR(2),
            hour VARCHAR(2)
        );
        
        CREATE INDEX IF NOT EXISTS idx_user_id ON prosthesis_sensor_facts(user_id);
        CREATE INDEX IF NOT EXISTS idx_signal_time ON prosthesis_sensor_facts(signal_time);
    """,
    dag=dag
)


def load_data_to_postgres(**context):
    """Загружает данные из XCom в PostgreSQL"""
    from airflow.hooks.postgres_hook import PostgresHook
    
    ti = context['task_instance']
    telemetry_data = ti.xcom_pull(task_ids='load_telemetry_task', key='telemetry_data')
    users_data = ti.xcom_pull(task_ids='load_users_task', key='users_data')
    
    pg_hook = PostgresHook(postgres_conn_id='write_to_postgres')
    
    # Очищаем временные таблицы
    pg_hook.run("TRUNCATE TABLE temp_telemetry, temp_users;")
    
    # Вставляем телеметрию
    for record in telemetry_data:
        pg_hook.run("""
            INSERT INTO temp_telemetry 
            (user_id, prosthesis_type, muscle_group, signal_frequency, 
             signal_duration, signal_amplitude, signal_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, parameters=(
            record['user_id'], 
            record['prosthesis_type'], 
            record['muscle_group'],
            record['signal_frequency'], 
            record['signal_duration'],
            record['signal_amplitude'], 
            record['signal_time']
        ))
    print(f"✅ телеметрия загружена в PostgreSQL")
    # Вставляем пользователей
    for record in users_data:
        pg_hook.run("""
            INSERT INTO temp_users 
            (user_id, name, email, age, gender, country, address, phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, parameters=(
            record['user_id'], 
            record['name'], 
            record['email'], 
            record['age'],
            record['gender'], 
            record['country'], 
            record['address'], 
            record['phone']
        ))
    print(f"✅ пользователи загружены в PostgreSQL")
    # Выполняем MERGE (INSERT) в основную таблицу
    result = pg_hook.run("""
        INSERT INTO prosthesis_sensor_facts (
            user_id, prosthesis_type, muscle_group, 
            signal_frequency, signal_duration, signal_amplitude, 
            signal_time, user_name, user_email, user_age, 
            user_gender, user_country, user_address, user_phone, 
            load_date, year, month, day, hour
        )
        SELECT 
            t.user_id, 
            t.prosthesis_type, 
            t.muscle_group,
            t.signal_frequency, 
            t.signal_duration, 
            t.signal_amplitude,
            t.signal_time,
            u.name, 
            u.email, 
            u.age, 
            u.gender, 
            u.country, 
            u.address, 
            u.phone,
            CURRENT_DATE,
            TO_CHAR(t.signal_time, 'YYYY'),
            TO_CHAR(t.signal_time, 'MM'),
            TO_CHAR(t.signal_time, 'DD'),
            TO_CHAR(t.signal_time, 'HH24')
        FROM temp_telemetry t
        LEFT JOIN temp_users u ON t.user_id = u.user_id;
        
        SELECT COUNT(*) FROM prosthesis_sensor_facts WHERE load_date = CURRENT_DATE;
    """,
    autocommit=True)
    
    print(f"✅ Данные загружены в PostgreSQL")
    
    # Очищаем XCom 
    #ti.xcom_clear(key='telemetry_data')
    #ti.xcom_clear(key='users_data')

load_to_postgres = PythonOperator(
    task_id='load_to_postgres',
    python_callable=load_data_to_postgres,
    dag=dag
)


# Зависимости
start >> create_temp_tables >> [load_telemetry_task, load_users_task] >> create_facts_table >> load_to_postgres