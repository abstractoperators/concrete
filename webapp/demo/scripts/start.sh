#!/bin/sh
cd /app
echo "Starting celery worker"
celery -A concrete worker --loglevel=DEBUG --detach --logfile=/app/celery.log

# TODO supervisord?
# Start a background process to tail the Celery log
tail -f /app/celery.log &

cd /app/webapp/demo
echo "Starting gunicorn server"
poetry run gunicorn server:app --bind 0.0.0.0:80 --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 1 --timeout=2000