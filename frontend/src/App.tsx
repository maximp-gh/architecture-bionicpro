// App.tsx - весь фронтенд в одном файле
import React, { useEffect, useState } from 'react';
import axios from 'axios';

// ============================================
// НАСТРОЙКИ
// ============================================
//const BACKEND_URL  = 'http://bionicpro-auth:3001';
//const FRONTEND_URL = 'http://frontend:3000';

const BACKEND_URL  = 'http://localhost:3001';
const FRONTEND_URL = 'http://localhost:3000';


// Создаем axios с настройкой для отправки cookie
const api = axios.create({
  baseURL: BACKEND_URL,
  withCredentials: true,  // ← отправляем httpOnly cookie
  headers: { 'Content-Type': 'application/json' }
});

// ============================================
// КОМПОНЕНТ СТРАНИЦЫ ЛОГИНА
// ============================================
const LoginPage: React.FC = () => {
  const handleLogin = () => {
    // Просто переходим на бэкенд, он сам перенаправит на Keycloak
    window.location.href = `${BACKEND_URL}/auth/login?redirect_uri=${FRONTEND_URL}`;
  };

return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <button
          onClick={handleLogin}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Login
        </button>
      </div>
    );
};

// ============================================
// КОМПОНЕНТ СТРАНИЦЫ ОТЧЕТОВ
// ============================================
const ReportPage: React.FC = () => {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState(null);

  useEffect(() => {
    const loadProfile = async () => {
      try {
        // Запрашиваем профиль - cookie отправится автоматически
        const response = await api.get('/api/user/profile');
        setProfile(response.data);
      } catch (error) {
        console.error('Failed to load profile:', error);
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, []);

  const downloadReport = async () => {
    // токена у нас нет, он на backend
    try {
      setLoading(true);
      setError(null);

      // Запрашиваем API...
      const response = await api.get(`http://localhost:3002/report`);
      if (response.status = 200) {
        setData (response.data)
      }
      else {
        setData (null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'A download error occurred');
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    // токена у нас нет, он на backend
    try {
      setError(null);

      // Запрашиваем API...
      const response = await api.post(`${BACKEND_URL}/auth/logout`);
      if (response.status = 201) {
        console.error ("Switching to login page")
        window.location.href = `${FRONTEND_URL}`;
      } 
      
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'A logout error occurred');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', marginTop: '50px' }}>Loading profile...</div>;
  }

  if (data) {
     return  <div >   <h3>Response:</h3>  <pre>{JSON.stringify(data, null, 2)}</pre>     </div> ;
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>
        
        <button
          onClick={downloadReport}
          disabled={loading}
          className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {loading ? 'Generating Report...' : 'Download Report'}
        </button>

        <button
          onClick={logout}
          disabled={loading}
          className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {loading ? 'Generating Report...' : 'Logout'}
        </button>

        {error && (
          <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================
// ГЛАВНЫЙ КОМПОНЕНТ APP
// ============================================
const App: React.FC = () => {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // Очищаем URL от параметров code/state если они есть
        if (window.location.search.includes('code=')) {
          window.history.replaceState({}, document.title, window.location.pathname);
        }

        // Запрашиваем статус аутентификации у бэкенда
        const response = await api.get('/api/auth/status');
        console.log (response)
        setAuthenticated(response.data.authenticated);
      } catch (error) {
        console.error('Auth check failed:', error);
        setAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuthStatus();
  }, []);

  // Пока проверяем статус
  if (loading) {
    return <div style={{ textAlign: 'center', marginTop: '50px' }}>Loading...</div>;
  }

  // Если не авторизован - показываем страницу логина
  if (!authenticated) {
    return <LoginPage />;
  }

  // Если авторизован - показываем страницу отчетов
  return <ReportPage />;
};

export default App;