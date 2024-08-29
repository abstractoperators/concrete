## Deploying new webapps to subdomains

* Create a directory e.g. homepage
* Create a corresponding dockerfile in `concrete/docker`, e.g. `Dockerfile.homepage`
* Use the previous dockerfile to upload an image to ecr. See `make build-webapp-homepage` and `make aws_ecr_push_homepage`
* To test locally, use `make run-webapp-[demo|homepage]`. Note that running the containers will not build, so you will need to build as appropriate. 
* Add these commands to GH actions through `concrete/.github/workflows/deploy_to_staging.yml`
  - Alternatively, call `poetry run python -m concrete deploy <image-uri> [--custom_name=<service-name>]`