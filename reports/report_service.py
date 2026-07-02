from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
#from datetime import datetime, timedelta
import httpx
import os
from dotenv import load_dotenv
from clickhouse_driver import Client
import json

load_dotenv()

# ============================================
# КОНФИГУРАЦИЯ
# ============================================
OAUTH_BACKEND_URL = os.getenv("OAUTH_BACKEND_URL", "http://localhost:3001")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "sample")
POSTGRES_USER = os.getenv("POSTGRES_USER", "airflow")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")
PORT = int(os.getenv("PORT", 3002))

# ============================================
# ИНИЦИАЛИЗАЦИЯ FASTAPI
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"✅ Report Service started on port {PORT}")
    print(f"✅ OAuth Backend: {OAUTH_BACKEND_URL}")
    print(f"✅ ClickHouse: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    yield

app = FastAPI(title="Report Service using CLickHouse", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# ПРОВЕРКА АУТЕНТИФИКАЦИИ ЧЕРЕЗ OAUTH BACKEND
# ============================================
async def verify_session_with_oauth(session_id: str) -> Dict[str, Any]:
    """
    Проверяет session_id через OAuth Backend.
    
    Args:
        session_id: ID сессии из cookie
    
    Returns:
        Dict с данными пользователя (user_id, username, email)
    
    Raises:
        HTTPException: Если сессия невалидна
    """
    async with httpx.AsyncClient() as client:
        try:
            # Получаем детальную информацию о пользователе
            user_response = await client.get(
                f"{OAUTH_BACKEND_URL}/api/user/profile",
                cookies={"session_id": session_id},
                timeout=10.0
            )
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                return {
                    "id": user_data.get("id"),
                    "user_id": user_data.get("user_id"),
                    "username": user_data.get("username"),
                    "email": user_data.get("email"),
                    "first_name": user_data.get("first_name"),
                    "last_name": user_data.get("last_name")
                }
            else:
                # Если не удалось получить профиль, используем базовые данные
                raise HTTPException(503, "Unknown user")
                
        except httpx.TimeoutException:
            raise HTTPException(503, "OAuth backend timeout")
        except httpx.RequestError as e:
            raise HTTPException(503, f"OAuth backend unavailable: {str(e)}")


async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Dependency для получения текущего пользователя.
    Проверяет session_id через OAuth бэкенд.
    """
    session_id = request.cookies.get("session_id")
    
    if not session_id:
        raise HTTPException(401, "Missing session cookie")
    
    user = await verify_session_with_oauth(session_id)
    return user


def generate_report (user_email: str, user_id: int, start_day: str, end_day: str):
    # Делаем выборку из OLAP DB
    try:
        client = Client(
            host='olap_db',
            port=9000,
            user='default',
            password='default',  # пустой не работает
            database='default'
        )
        print (f"Подключились к ClickHouse, userid={user_id}")
        # Используем параметризованный запрос для безопасности
        query = """
        SELECT 
            user_id,
            prosthesis_type,
            muscle_group,
            signal_frequency,
            signal_duration,
            signal_amplitude,
            signal_time
        FROM emg_sensor_data
        WHERE user_id = %(user_id)s
                    AND signal_time::date >= %(start_time)s
                    AND signal_time::date <= %(end_time)s
        ORDER BY signal_time DESC
        """

        # Параметры запроса
        params = {'user_email': "2", 'user_id': user_id, 'start_time': start_day, 'end_time': end_day}

        # Выполняем с параметрами
        result = client.execute(query, params, with_column_types=True)

        # result содержит данные и информацию о колонках
        data = result[0]          # сами данные
        columns = result[1]       # информация о колонках

        # Выводим с заголовками
        headers = [col[0] for col in columns]
        print(" | ".join(headers))
        print("-" * 80)

        for row in data:
            print(" | ".join(str(val) for val in row))

        # Преобразуем datetime в строку
        #for row in data:
        #    if row['signal_time']:
        #        row['signal_time'] = row['signal_time'].isoformat()
        
        return {
            "user_email": user_email,
            "period": {
                "start": start_day,
                "end": end_day
            },
            "total": len(data),
            "data": data
        }
    except () as e:
        print (e)   
    finally:
        print ("Got to finally...")
        #cur.close()
        #conn.close()



# ============================================
# ЭНДПОИНТЫ
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "report-service"}


@app.get("/report")
async def get_report(
    request: Request,
    start_day: Optional[str] = "2024-01-01",
    end_day: Optional[str] = "2025-03-06"
):
    """
    Простая выборка данных пользователя за период.
    
    Параметры:
    - start_day: дата начала (YYYY-MM-DD)
    - end_day: дата окончания (YYYY-MM-DD)
    """
    # 1. Проверяем сессию и получаем email пользователя
    user = await get_current_user(request)
    user_email = user.get("email")
    user_id = user.get("user_id")
    
    if not user_id or not user_email:
        raise HTTPException(400, "User_id not found")
    
    print (user_email)


    #Сначала проверим наличие в S3/CDN
    key = f"prosthesis/{user_id}/{start_day}_{end_day}/report.txt"
    
    from s3 import S3Client
    async with S3Client() as s3c:
        
        cdn_url = await s3c.get_cdn_url(key)
        
        if cdn_url:
            return {"cdn_url": cdn_url}
        
        # Генерация отчёта
        content = generate_report(user_email, user_id, start_day, end_day)
        
        # Кладем отчет в S3
        await s3c.client.put_object(
            Bucket='reports-bucket',
            Key=key,
            Body=json.dumps(content, default=str).encode('utf-8'),  # dict → JSON → bytes
            )
        
        # Возвращаем ссылку (должна матчится с nginx.conf): "reports"->"reports_bucket"
        return {"cdn_url": f"http://localhost:8090/reports/{key}"}


# ============================================
# ЗАПУСК
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)