FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV APP_PORT=8000

CMD ["sh", "-c", "python /app/app/migrate.py && uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}"]