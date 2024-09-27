#!/bin/sh

cd webapp/homepage
gunicorn server:app --bind 0.0.0.0:80 --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 1 --timeout=2000# Module Documentation

## Description
This module is a shell script that starts a Gunicorn server for a web application located in the `webapp/homepage` directory. It is configured to serve the application using Uvicorn as the worker class, which is suitable for handling asynchronous requests.

## Usage
To execute this script, ensure that you have the necessary permissions and that the required dependencies (Gunicorn and Uvicorn) are installed in your environment. Run the script from the command line to start the server.

## Parameters
- `--bind 0.0.0.0:80`: Binds the server to all available IP addresses on port 80.
- `--workers 1`: Specifies the number of worker processes to handle requests. In this case, it is set to 1.
- `--worker-class uvicorn.workers.UvicornWorker`: Uses Uvicorn as the worker class, allowing for asynchronous request handling.
- `--threads 1`: Sets the number of threads per worker to 1.
- `--timeout=2000`: Configures the timeout for requests to 2000 seconds, which is unusually high and may need to be adjusted based on application requirements.

## Notes
- Ensure that the server is not already running on port 80 to avoid conflicts.
- Consider adjusting the number of workers and threads based on the expected load and performance requirements of the application.