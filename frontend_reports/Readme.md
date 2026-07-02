1. Пользователь логинится через OAuth Backend
   ↓
2. OAuth Backend устанавливает session_id cookie
   ↓
3. Фронтенд делает запрос к Report Service
   GET http://localhost:3002/report?start_date=...
   Cookie: session_id=abc123
   ↓
4. Report Service получает session_id из cookie
   ↓
5. Report Service проверяет session_id через OAuth Backend
   GET http://localhost:3000/api/auth/status
   Cookie: session_id=abc123
   ↓
6. OAuth Backend подтверждает, что сессия валидна
   Возвращает данные пользователя
   ↓
7. Report Service знает user_id и email
   ↓
8. Report Service делает запрос в PostgreSQL
   WHERE user_id = 'user-123'
   ↓
9. Report Service возвращает ТОЛЬКО данные этого пользователя
   ↓
10. Фронтенд получает отчет