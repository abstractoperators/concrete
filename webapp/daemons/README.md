# How to develop webhooks locally
Webhooks require a URL to be able to send requests to. This is a problem when developing locally, as the webhook URL is not accessible from the internet. To solve this problem, I use ngrok to create a tunnel to my local machine. This allows me to expose my local server to the internet, and receive requests from the webhook.

## Steps to create a tunnel with ngrok
1. [Install Ngrok](https://dashboard.ngrok.com/get-started/setup/linux)
2. Start ngrok `ngrok http http://localhost:8000`
3. Start your local server (e.g. `poetry run fastapi dev server.py`)
4. Copy the forwarding URL from ngrok console, and use it as the webhook URL.

# GH Daemon
.env.daemons requires the following variables:
1. GH_WEBHOOK_SECRET=...
2. GH_CLIENT_ID=...
3. GH_PRIVATE_KEY_PATH=... 
