#!/bin/sh

set -a;
source .env
echo $DB_DRIVER
alembic upgrade head