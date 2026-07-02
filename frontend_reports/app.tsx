// src/services/api.ts
import axios from 'axios';

// OAuth бэкенд (для аутентификации)
export const authApi = axios.create({
  baseURL: 'http://localhost:3001',
  withCredentials: true,
});

// Report сервис (для данных)
export const reportApi = axios.create({
  baseURL: 'http://localhost:3002',
  withCredentials: true,  // session_id cookie отправится автоматически
});

// Использование
export const getReports = async (startDate: string, endDate: string) => {
  const response = await reportApi.get('/report', {
    params: { start_date: startDate, end_date: endDate }
  });
  return response.data;
};