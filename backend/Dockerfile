FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN addgroup --system carevia && adduser --system --ingroup carevia carevia

COPY requirements /app/requirements
RUN pip install --no-cache-dir -r /app/requirements/prod.txt

COPY . /app
RUN python manage.py collectstatic --noinput && chown -R carevia:carevia /app

USER carevia
EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "2", "--timeout", "60", "--access-logfile", "-"]
