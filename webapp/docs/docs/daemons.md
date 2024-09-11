## Daemons

### GH Daemon
Represents a GitHub PR Daemon. It can autonomously create branches, commits, and pull requests. It is responsible for making trivial changes, such as updating code style, adding documentation, or fixing typos.
It will detect PRs created by users. It will create its own revision branch, make commits with changes, and create a PR into the original branch.

#### env vars
Loaded in from `.env.daemons` at build-time.

- GH_WEBHOOK_SECRET
  - Webhook secret defined in GitHub App settings.
- GH_CLIENT_ID=Iv23liFWaaYI9wJnczp0
  - App client id.
- GH_PRIVATE_KEY_PATH='concreteoperator.2024-09-10.private-key.pem'
  - Path to *.pem file relative to `webapp/daemon/server.py`.
