#!/bin/sh

echo $DB_DRIVER
uv run alembic upgrade head