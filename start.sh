#!/bin/sh

cd /app/demo_webapp
ls

poetry run gunicorn server:app --bind 0.0.0.0:80 --workers 2 --worker-class uvicorn.workers.UvicornWorker --threads=2 --timeout=200