FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install --no-cache-dir flask requests python-dotenv

# App code (images/db/data are mounted as volumes by docker-compose.yml)
COPY backend/ ./backend/
COPY templates/ ./templates/
COPY static/css/ ./static/css/
COPY static/js/ ./static/js/

EXPOSE 5000

CMD ["python", "backend/run_portal.py"]
