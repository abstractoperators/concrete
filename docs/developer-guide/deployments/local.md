# Local Deployments

It's often necessary, and recommended, to deploy our services locally while making changes to them.
Here are some things you ought to know to ensure a painless local deployment experience.

## Web Dev

### Allow local subdomains

By default, auth will be enabled on webapps even when run locally.
This requires an auth service to be run, which is hosted at a sub-domain in staging/prod.
To mirror this setup locally add the following lines to the bottom of `/etc/hosts`:

```
127.0.0.1 abop.bot auth.abop.bot
```