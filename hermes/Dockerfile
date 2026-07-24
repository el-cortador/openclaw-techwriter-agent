FROM python:3.11-slim

WORKDIR /app

COPY hermes/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY hermes/app/ /app/app/
COPY runtimes/hermes/skills/ /app/skills/

CMD ["python", "-m", "app.main"]
