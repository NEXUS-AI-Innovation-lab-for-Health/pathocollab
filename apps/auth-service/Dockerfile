FROM python:3.11

WORKDIR /app

RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD sh -c "until pg_isready -h postgres -p 5432 -U pixtral_user; do echo 'Waiting for postgres...'; sleep 2; done; alembic upgrade head; uvicorn app.main:app --host 0.0.0.0 --port 8001"