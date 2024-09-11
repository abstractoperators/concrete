## Daemons

### GH Daemon
Represents a GitHub PR Daemon.
Daemon can act on many installations, orgs/repos/branches.
See https://www.notion.so/Proactive-D-mons-a6ad32c5b4dd4f43969b3a7c6a630c17?pvs=4

#### env vars
Loaded in from `.env.daemons` at build-time.

- GH_WEBHOOK_SECRET
  - Webhook secret defined in GitHub App settings.
- GH_CLIENT_ID=Iv23liFWaaYI9wJnczp0
  - App client id.
- GH_PRIVATE_KEY_PATH='concreteoperator.2024-09-10.private-key.pem'
  - Path to *.pem file relative to `webapp/daemon/server.py`.
