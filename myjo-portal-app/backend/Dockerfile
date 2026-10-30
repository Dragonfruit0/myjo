FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UPLOAD_DIR=/data/uploads
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY wsgi.py .

RUN useradd --create-home myjo && mkdir -p /data/uploads && chown -R myjo /data
USER myjo

EXPOSE 5000
# 4 workers is right for a 2-CPU server; raise to (2 x CPUs) + 1 on bigger machines.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "wsgi:app"]
