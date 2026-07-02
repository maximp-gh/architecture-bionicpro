from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import os
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel
from keycloak import KeycloakOpenID

# session_encryption.py
from cryptography.fernet import Fernet
import base64
import os

# Генерируем ключ для шифрования (лучше сохранить в переменную окружения)
ENCRYPTION_KEY = base64.urlsafe_b64encode(os.urandom(32))
cipher = Fernet(ENCRYPTION_KEY)

def encrypt_token(token: str) -> str:
    """Шифрует токен"""
    if not token:
        return None
    encrypted = cipher.encrypt(token.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Расшифровывает токен"""
    if not encrypted_token:
        return None
    encrypted = base64.urlsafe_b64decode(encrypted_token.encode())
    decrypted = cipher.decrypt(encrypted)
    return decrypted.decode()


load_dotenv(find_dotenv())

# ========== Models ==========
class TokenRequest(BaseModel):
    grant_type: str
    code: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: str
    code_verifier: Optional[str] = None
    redirect_uri: Optional[str] = None

class UserInfo(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: list[str] = []

# ========== Keycloak Client ==========
keycloak_openid = KeycloakOpenID(
    server_url=os.getenv("SRV_KEYCLOAK_URL"),
    client_id=os.getenv("SRV_KEYCLOAK_CLIENT_ID"),
    realm_name=os.getenv("SRV_KEYCLOAK_REALM"),
    #client_secret_key=os.getenv("SRV_KEYCLOAK_CLIENT_SECRET") or None,
    verify=True
)

# ========== Session Storage (in-memory, можно Redis в production) ==========
sessions: Dict[str, Dict[str, Any]] = {}
oauth_states: Dict[str, Dict[str, Any]] = {}  # Храним state для защиты от CSRF

def create_session(user_id: str, username: str, refresh_token: str, access_token: str, access_token_expires_at: datetime) -> str:
    """Создание новой сессии"""
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {
        "user_id": user_id,
        "username": username,
        "refresh_token": refresh_token,
        "access_token": access_token,
        "access_token_expires_at": access_token_expires_at,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=int(os.getenv("SESSION_EXPIRY_DAYS", 1)))
    }
    return session_id

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Получение сессии по ID"""
    session = sessions.get(session_id)
    if session and session["expires_at"] > datetime.utcnow():
        return session
    if session_id in sessions:
        del sessions[session_id]
    return None

def delete_session(session_id: str):
    """Удаление сессии"""
    if session_id in sessions:
        del sessions[session_id]

def save_oauth_state(state: str, redirect_uri: str, code_challenge: str = None):
    """Сохранение state для проверки callback"""
    oauth_states[state] = {
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "created_at": datetime.utcnow()
    }

def get_and_delete_oauth_state(state: str) -> Optional[Dict[str, Any]]:
    """Получение и удаление state"""
    data = oauth_states.get(state)
    if data:
        del oauth_states[state]
    return data

# ========== FastAPI App ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"✅ Keycloak server: {os.getenv('SRV_KEYCLOAK_URL')}")
    print(f"✅ Realm: {os.getenv('SRV_KEYCLOAK_REALM')}")
    print(f"✅ Client: {os.getenv('SRV_KEYCLOAK_CLIENT_ID')}")
    print(f"✅ Frontend URL: {os.getenv('FRONTEND_URL')}")
    yield

app = FastAPI(title="OAuth2 with Keycloak Redirect Flow", lifespan=lifespan)

from keycloak.pkce_utils import generate_code_verifier, generate_code_challenge
# Generate PKCE values
code_verifier = generate_code_verifier()

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://frontend:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Helper Functions ==========
async def get_current_user(request: Request) -> UserInfo:
    """Dependency для получения текущего пользователя из сессии"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(401, "Not authenticated")
    
    session = get_session(session_id)
    if not session:
        raise HTTPException(401, "Session expired")
    
    # Обновляем access token через refresh token
    try:
        tokens = keycloak_openid.refresh_token(decrypt_token(session['refresh_token']))
        userinfo = keycloak_openid.userinfo(tokens['access_token'])
        
        # Обновляем refresh token в сессии если Keycloak выдал новый
        if 'refresh_token' in tokens:
            session['refresh_token'] = encrypt_token(tokens['refresh_token'])
        
        # Извлекаем роли
        roles = userinfo.get('realm_access', {}).get('roles', [])
        
        return UserInfo(
            id=userinfo['sub'],
            username=userinfo.get('preferred_username', userinfo.get('email', '')),
            email=userinfo.get('email'),
            first_name=userinfo.get('given_name'),
            last_name=userinfo.get('family_name'),
            roles=roles
        )
        
    except Exception as e:
        delete_session(session_id)
        raise HTTPException(401, f"Session invalid: {str(e)}")

# ========== OAuth2 Redirect Flow Endpoints ==========
@app.get("/auth/login")
async def auth_login(
    redirect_uri: str,
    code_challenge: Optional[str] = None
):
    """
    Эндпоинт для начала OAuth2 потока.
    Перенаправляет пользователя на страницу логина Keycloak.
    """
    # Генерируем state для защиты от CSRF
    state = secrets.token_urlsafe(32)
    
    # Сохраняем параметры для последующего использования в callback
    oauth_states[state] = {
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge
    }
    
    code_challenge, code_challenge_method = generate_code_challenge(code_verifier)


    # Строим URL для редиректа на Keycloak
    auth_url = keycloak_openid.auth_url(
        redirect_uri=f"http://localhost:{os.getenv('PORT', 3001)}/auth/callback",
        scope="openid profile email",
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method
        #code_challenge_method="S256" if code_challenge else None
    )
    
    # Перенаправляем пользователя на страницу логина Keycloak
    return RedirectResponse(url=auth_url)

@app.get("/auth/callback")
async def auth_callback(
    code: str,
    state: str,
    session_state: str
):
    """
    Callback от Keycloak после логина.
    Логин редиректит на Keycloak, Keycloak редиректит сюда.
    """

    print(f"✅ БЭКЕНД ПЕРЕХВАТИЛ CODE: {code}...") 
    try:
        # Обмениваем code на токены (используя client_secret)
        tokens = keycloak_openid.token(
            grant_type="authorization_code",
            code=code,
            redirect_uri=f"http://localhost:{os.getenv('PORT', 3001)}/auth/callback",
            code_verifier=code_verifier
        )
        
        # Получаем информацию о пользователе
        userinfo = keycloak_openid.userinfo(tokens['access_token'])
        
        print(f"✅ user: {userinfo}...")
        # Создаем сессию и сохраняем tokens на сервере
        session_id = create_session(
            user_id=userinfo['sub'],
            username=userinfo.get('preferred_username', userinfo.get('email', '')),
            refresh_token=encrypt_token(tokens['refresh_token']),  # Храним на сервере!
            access_token=tokens['access_token'],
            access_token_expires_at = datetime.utcnow() + timedelta(seconds=tokens['expires_in'])

        )
        
        # Редиректим на фронтенд с session cookie
        frontend_url = os.getenv("FRONTEND_URL", "http://frontend:3000")
        response = RedirectResponse(url=f"{frontend_url}")
        print ("response")
        # Устанавливаем httpOnly cookie (токен недоступен из JS)
        is_production = os.getenv("ENVIRONMENT") == "production"
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=is_production,
            samesite="lax",
            max_age=7 * 24 * 60 * 60,
            path="/"
        )
        
        return response
        
    except Exception as e:
        print(f"Callback error: {e}")
        raise HTTPException(400, f"Authentication failed: {str(e)}")

@app.get("/api/auth/status")
async def auth_status(request: Request):
    """Проверка статуса аутентификации"""
    session_id = request.cookies.get("session_id")

    print(f"✅ session_id: {session_id}")
    
    if not session_id:
        print(f"Not authenticated 1")
        return {"authenticated": False}
    
    session = get_session(session_id)
    if not session:
        print(f"Not authenticated 2")
        return {"authenticated": False}
    
    print(f"Authenticated!!!")
    return {
        "authenticated": True,
        "user": {
            "id": session['user_id'],
            "username": session['username']
        }
    }

@app.post("/auth/logout")
async def logout(request: Request):
    """Выход из системы"""
    session_id = request.cookies.get("session_id")
    
    if session_id:
        session = get_session(session_id)
        if session:
            try:
                # Отзываем refresh_token в Keycloak
                keycloak_openid.logout(decrypt_token(session['refresh_token']))
            except:
                pass
        delete_session(session_id)
    
    response = JSONResponse({"success": True})
    response.status_code = 201
    response.delete_cookie("session_id", path="/")
    return response

@app.get("/api/user/profile")
async def get_profile(request: Request):
    """Получение профиля пользователя (токены на сервере)"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(401, "Not authenticated")
    
    session = get_session(session_id)
    if not session:
        raise HTTPException(401, "Session expired")
    
    new_session_id = None
    try:
        # Используем refresh_token с сервера для получения нового access_token

        if datetime.utcnow() > session['access_token_expires_at']:
            tokens = keycloak_openid.refresh_token(decrypt_token(session['refresh_token']))    
            print ("Обновление access_token пр помощи refresh_token")
            # Обновляем refresh_token если Keycloak выдал новый
            session['access_token'] = tokens['access_token']
            session['access_token_expires_at'] = datetime.utcnow() + timedelta(seconds=tokens['expires_in'])
            if 'refresh_token' in tokens:
                session['refresh_token'] = encrypt_token(tokens['refresh_token'])

            # session rotation
            new_session_id = secrets.token_urlsafe(32)
            sessions[new_session_id] = session
            delete_session(session_id)  # удаляем старую
            
       
        userinfo = keycloak_openid.userinfo(session['access_token'])

        print (userinfo)
        # Realm-роли пользователя
       

        #def has_role(token: str, role_name: str, client_id: str | None = None) -> bool:
        #    try:
        #        payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
        #    except (InvalidTokenError, ExpiredSignatureError):
        #        return False
        #
        #    # Проверка realm‑роли
        #    if role_name in payload.get("realm_access", {}).get("roles", []):
        #        return True
        #   return false


        options = {
            "verify_aud": False,      # Disable audience check
            "verify_signature": True,  # Keep signature verification
            "verify_exp": True         # Keep expiration check
        }



        #import jwt

        #Публичный ключ из keycloak realm settings
        PUBLIC_KEY= """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvgsJz8wje7zaybu76JM6T4N+ErSNB16CHZKn2ENfN/aAdDfuKQIk5W8RuGLpvtbCBQ1xTkzg9JIeLGLSvhzRlIy230h9uETSr6lLXbExyLQF+xQJbf5HVf3btydkl8Tk/M53ezz64ip48Xj65UPFYLzX5vurieWrEJ+H4q7sWhtr5AWwfrIx5ApyKu1Flh3mtvUn1Misj/DhjGKGFC8rzaJZAvlEFguRLIvTAE8W3LJmf4ZaHxAWFyM8DNEtJJsiuf3MLniduKIPYGlh3JAlZPlnOrZBrfya3X+NPzLqvDSeD087a/lxMSRyCbTD0Yx+VHgXYEKURmn8MLuM+9Me9wIDAQAB
-----END PUBLIC KEY-----"""
        
        try:
            payload = keycloak_openid.decode_token(
                session['access_token'],
                #options=options
            )
            #payload = jwt.decode(
            #    session['access_token'],
            #    PUBLIC_KEY,
            #    algorithms=["RS256"],
            #    #options={"verify_aud": False},  # отключает проверку audience
            #    #audience=os.getenv("SRV_KEYCLOAK_CLIENT_ID"),  # <-- client_id вашего клиента в Keycloak
            #    )
            
        except () as e:
            print (e)
            return HTTPException(401, "Token error")

        #print (payload)
        realm_roles = payload.get("realm_access", {}).get("roles", [])

        print("Realm roles:", [r for r in realm_roles])
        
        resp = {
            "id": userinfo['sub'],
            "user_id": userinfo.get('user_id'),
            "username": userinfo.get('preferred_username', userinfo.get('email')),
            "email": userinfo.get('email'),
            "first_name": userinfo.get('given_name'),
            "last_name": userinfo.get('family_name'),
            "realmRoles": realm_roles
        }
        response = JSONResponse(content=resp)
        if not new_session_id is None:
            print ("Ротация сессии")
            response.set_cookie(
                key="session_id",
                value=new_session_id,
                httponly=True,
                secure=os.getenv("ENVIRONMENT") == "production",
                samesite="lax",
                path="/"
            )
        
        return response

        
    except Exception as e:
        print (e)
        delete_session(session_id)
        raise HTTPException(401, "Session invalid")

@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3001))
    uvicorn.run(app, host="0.0.0.0", port=port)