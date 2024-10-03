#!/bin/sh

# cd /app/webapp/main
gunicorn webapp.main.server:app --bind 0.0.0.0:80 --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 1 --timeout=2000# Module Documentation

## Overview
This module is responsible for launching the web application using Gunicorn, a Python WSGI HTTP server. It is configured to serve the application defined in `webapp.main.server`.

## Configuration Options
- **--bind 0.0.0.0:80**: This option specifies the address and port on which the server will listen for incoming requests. In this case, it binds to all available interfaces on port 80.
- **--workers 1**: This option sets the number of worker processes for handling requests. A value of 1 means that only one worker will be used.
- **--worker-class uvicorn.workers.UvicornWorker**: This specifies the worker class to be used. UvicornWorker is an ASGI server that allows for handling asynchronous requests, making it suitable for applications that require high concurrency.
- **--threads 1**: This option defines the number of threads per worker. A value of 1 indicates that each worker will handle one request at a time.
- **--timeout=2000**: This sets the timeout for requests in seconds. A value of 2000 seconds allows for long-running requests without timing out.

## Usage
To start the web application, execute this script in a shell environment. Ensure that the necessary dependencies, including Gunicorn and Uvicorn, are installed in your Python environment.