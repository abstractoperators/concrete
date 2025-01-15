# How to develop locally

Webhooks require a URL to be able to send requests to. This is a problem when developing locally, as the webhook URL is not accessible from the internet. To solve this problem, I use ngrok to create a tunnel to my local machine. This allows me to expose my local server to the internet, and receive requests from the webhook.

## Steps to create a tunnel with ngrok

1. [Install Ngrok](https://dashboard.ngrok.com/get-started/setup/linux)
2. Start ngrok `make ngrok`
3. Start your local server (e.g., make local-agentserver)
4. Copy the forwarding URL from ngrok console, and use it as the webhook URL. For the Slack Daemon, https://api.slack.com/apps/A07P0F0TK2L/slash-commands?)

# Jaime

## Env

.env requires the following variables for Slack Daemon

```.env
SLACK_SIGNING_SECRET=
SLACK_BOT_TOKEN=
HTTP_SESSION_SECRET
HTTP_SESSION_DOMAIN
OPENAI_API_KEY=

# For logging (leave blank to use sqlite)
DB_DRIVER=
DB_USERNAME=
DB_PASSWORD=
DB_PORT=
DB_HOST=
DB_DATABASE=

```


## Deploying to another cloud/slack workspace

1. Create a new Slack App
   1. Create a bot user, and give it permissions to write messages, write messages with customized avatar, join channels, write to public channels, and add commands.
2. Add signing secret and bot token to .env
3. Update the Slack App's slash command URL to the deployed server (at endpoint `/slack/slash-commands`)
4. Create auth server that updates session secrets
5. Update http session secret and domain
6. Potentially configure a db for logging

Lines Changed: +47, -0
Last Updated: 2025-01-15 02:47:48 UTC