# Requirements

webapp-demo requires dind-builder to be running to have build capabilities.

webapp-demo requires environment variables. These can be placed in a `.env` file, which will be loaded at runtime by the container. The following environment variables are required:
- `OPENAI_API_KEY`
- For deployment (including main to prod)
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
- For slack button
  - `SLACK_BOT_TOKEN`
  - Required for the slack button to send messages to channels.


# Slack Button
The following is the manifest and process of setting up the Slack button

```json manifest
{
    "display_information": {
        "name": "GH Deploy" 
    },
    "features": {
        "bot_user": {
            "display_name": "GH Deploy",
            "always_online": true
        }
    },
    "oauth_config": {
        "scopes": {
            "bot": [
                "chat:write",
                "channels:history"
            ]
        }
    },
    "settings": {
        "event_subscriptions": {
            "request_url": "https://webapp-demo-staging.abop.ai/slack/events",
            "bot_events": [
                "message.channels"
            ]
        },
        "interactivity": {
            "is_enabled": true,
            "request_url": "https://webapp-demo-staging.abop.ai/slack"
        },
        "org_deploy_enabled": false,
        "socket_mode_enabled": false,
        "token_rotation_enabled": false
    }
}
```

Event Subscriptions: Slack sends out a post request to `request_url` whenever a `bot_event` occurs. In this case, we listen for messages being sent to channels. Refer to [message events](https://api.slack.com/events/message) for more details. Your app bot must be added to the channel in order to receive these events. 

Server side, we respond to these requests in `webapp-demo`. The `slack/events` endpoint listens for these requests, and publishes a button to #github-logs under the condition that the message is in #github-logs, and is a merge message from the (official) Github bot. 

Interactivity (e.g. Buttons): When a user interacts with any interactive modality, Slack sends a post request to `request_url`. In this case, it sends it to `webapp-demo-staging.abop.ai/slack/`. This endpoint deploys the latest commit on `main` to prod. More specifically, it deploys the latest containers in ECR (008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-<demo|homepage>:latest).
# Module Overview

The `webapp-demo` module is responsible for serving the web application using the Gunicorn server. It is designed to handle incoming requests and manage the application lifecycle effectively.

## Startup Script
The module is initiated through a shell script that sets up the environment and starts the Gunicorn server. The script performs the following actions:

```sh
#!/bin/sh
cd webapp/demo
echo "Starting gunicorn server"
gunicorn server:app --bind 0.0.0.0:80 --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 1 --timeout=2000
```

### Breakdown of the Startup Script:
- `#!/bin/sh`: This line indicates that the script should be run in a shell environment.
- `cd webapp/demo`: Changes the current directory to `webapp/demo`, where the application code resides.
- `echo "Starting gunicorn server"`: Outputs a message to the console indicating that the Gunicorn server is starting.
- `gunicorn server:app --bind 0.0.0.0:80 --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 1 --timeout=2000`: This command starts the Gunicorn server with the following parameters:
  - `server:app`: Specifies the application to run, where `server` is the module and `app` is the application instance.
  - `--bind 0.0.0.0:80`: Binds the server to all available IP addresses on port 80.
  - `--workers 1`: Sets the number of worker processes to handle requests. In this case, it is set to 1.
  - `--worker-class uvicorn.workers.UvicornWorker`: Uses Uvicorn as the worker class for handling asynchronous requests.
  - `--threads 1`: Specifies the number of threads per worker.
  - `--timeout=2000`: Sets the timeout for requests to 2000 seconds, allowing long-running requests to complete.

## Deployment Considerations
Ensure that the environment is properly configured with the required environment variables before starting the Gunicorn server. The server should be monitored for performance and errors to ensure optimal operation.