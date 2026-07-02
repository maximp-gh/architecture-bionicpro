FROM python:3.12.1-slim
WORKDIR /app
# Копирование кода приложения
COPY . .
EXPOSE 3002
# Устанавливаем зависимости python не пересобирая их
RUN pip install --no-cache --no-cache-dir -r requirements.txt
ENTRYPOINT ["uvicorn"]
CMD ["report_service:app", "--host", "0.0.0.0", "--port", "3002"]
