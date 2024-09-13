
## Deploying new webapps to subdomains

* Create a directory e.g. homepage
* Create a corresponding dockerfile in `concrete/docker`, e.g. `Dockerfile.homepage`
* Use the previous dockerfile to upload an image to ecr. See `make build-webapp-homepage` and `make aws_ecr_push_homepage`
* To test locally, use `make run-webapp-[demo|homepage]`. Note that running the containers will not build, so you will need to build as appropriate. 
* Add these commands to GH actions through `concrete/.github/workflows/deploy_to_staging.yml`
  - Alternatively, call `poetry run python -m concrete deploy --image_uri  <image_uri> --container_name <container_name> --container_port <container_port> [--service_name=<custom_service_name>]`
  

## Deploying webapps to tailscale network

* Create a directory e.g. homepage
* Create a corresponding dockerfile in `concrete/docker`, e.g. `Dockerfile.homepage`
* Add a corresponding entry in `concrete/docker-compose.yml`
  * Add a `ts-oauth-[...]` service to the `services` section, e.g. `ts-oauth-homepage`
  * Add a service corresponding to your webapp, e.g. `webapp-homepage`
    * Requires `network_mode: service:ts-oauth-[...]` to proxy through the tailscale network.
  * Set `TS_AUTHKEY` as an environment variable (I threw mine into zshrc - docker-compose won't be calling load_dotenv, so don't rely on .env files)
    * OAuth key is hinted with tags. Can re-use OAuth key for multiple services.
    * Auth keys don't have tags. Need to create a new one for each service.
* Run `docker compose -f docker/docker-compose.yml up -d [your_service]` (see `make run-webapp-[demo|homepage]` for examples)
* Navigate to [tailscale](https://login.tailscale.com/admin/machines) to verify that the service is running.
* Navigate to `http://<ts_service_name[-i]` to view the service. e.g. `http://ts-oauth-demo-1`.

Optional:
* To make localhost work, add ports to the `ts-oauth-[...]` service in `docker-compose.yml` and run as usual

## Docs server
Use the make commands from root of concrete

```bash
make build-docs
make run-docs
```