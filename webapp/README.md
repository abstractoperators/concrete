
## Deploying new webapps to subdomains

* Create a directory e.g. homepage
* Create a corresponding dockerfile in `concrete/docker`, e.g. `Dockerfile.homepage`
* Use the previous dockerfile to upload an image to ecr. See `make build-webapp-homepage` and `make aws-ecr-push-homepage`
* To test locally, use `make run-webapp-[demo|homepage]`. Note that running the containers will not build, so you will need to build as appropriate. 
* Add these commands to GH actions through `concrete/.github/workflows/deploy_to_staging.yml`
  - Alternatively, call `poetry run python -m concrete deploy --image_uri  <image_uri> --container_name <container_name> --container_port <container_port> [--service_name=<custom_service_name>]`
* To delete the deployment, delete the service through ECS
  
## Deploying webapps to tailscale network locally

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

## Deploying webapps to tailscale network on AWS

Tailscale recommends installing its client on every device, but this isn't always feasible in AWS environments, particularly with ECS Fargate. Subnet routers offer an alternative solution.
Challenges:

* ECS Fargate doesn't expose container-level networking, preventing the use of Tailscale sidecar containers.
* Direct installation in webapp service containers faces network mounting and IP tables issues.
* Switching to EC2 instances potentially solves the problem requires significant refactoring.

Subnet Routing Solution:

* Services are not directly in the Tailnet; only the subnet router is.
* The router advertises access to the subnet containing the services, allowing communication since both are in the same VPC.
* The load balancer, which is not internet-facing, resides in the private subnet and directs traffic to the services.
* The subnet router advertises the IP of the internal load balancer, enabling anyone connected to the Tailnet to access it through the router.
* Route 53 requires alias subdomain records (e.g., `homepage-staging.abop.ai`) pointing to the internal load balancer for routing.
* When Tailnet users access that URL, the subnet router makes the internal load balancer reachable, allowing access to the service without public exposure.
 
### Actual Steps/Notes

Besides networking differences, deploying a webapp to staging is identical to deploying to production. The only difference is the subnet, security group, and listener/load balancer configuration. This is because the subnet router is the one who is actually connecting to tailnet.

1. Create and push a docker image to ECR as normal
2. Use `AwsTool._deploy_service` or the CLI to deploy the image to ECS.
   1. MUST SPECIFY subnet, security group, and listener ARN
   2. subnet: Must be a public subnet in the same availability zone as the load balancer.
      1. [there's other solutions besides public subnet, but this is easiest](https://stackoverflow.com/questions/61265108/aws-ecs-fargate-resourceinitializationerror-unable-to-pull-secrets-or-registry)
   3. security group: Must allow inbound traffic from the load balancer
   4. listener: http/https listener arn for the load balancer
      1. load balancer: An internal load balancer with security group only allowing inbound traffic from the subnet router.
   5. (Note that you don't need to create more of them, just specify the existing resources). Reference homepage_staging.yml for an example.
3. Add a route 53 A record pointing to the internal load balancer
   1. Subdomain is the service name.
   2. Necessary because there is a default *.abop.ai record pointing to prod load balancer (which points to prod homepage).

Subnet Router: You don't need to do anything to create the subnet router. It's on AWS already, and won't be reinstantiated or anything. SSH key to it is in `Tailscale Subnet Router` in 1Password, `ssh -i <key> ubuntu@3.81.140.147`. Initial creation entailed following this [tutorial](https://tailscale.com/kb/1019/subnets) to advertise the route for the CIDR blocks of the internal load balancer.

## Docs server
Use the make commands from root of concrete

```bash
make build-docs
make run-docs
```
