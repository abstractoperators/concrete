#!/bin/sh

uv run --no-dev gunicorn webapp.daemons.server:app --bind 0.0.0.0:80 --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 1 --timeout=2000