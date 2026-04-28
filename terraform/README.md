# Terraform for `dag-health-api` on GCP

## Architecture Overview

This Terraform project provisions the minimal but production-aligned GCP infrastructure required to run the Dockerized `dag-health-api` FastAPI service.

The application is stateless:

- it accepts a full DAG payload in each request
- it performs async health checks at request time
- it does not need a database
- it does not require persistent storage

Because of that, Cloud Run is a strong fit:

- managed container runtime
- HTTPS endpoint out of the box
- autoscaling, including scale-to-zero
- no VM or cluster management
- native integration with Cloud Logging and Cloud Monitoring

At a high level:

1. Docker images are stored in Artifact Registry.
2. Cloud Run deploys the container image.
3. A dedicated service account is attached to the Cloud Run service.
4. IAM makes unauthenticated invocation optional and configurable.
5. Cloud Logging captures request/application logs automatically.
6. Cloud Monitoring captures Cloud Run metrics automatically and raises alert policies for 5xx errors and high latency.

## Delivery Order

This repository is intended to be used in four distinct steps:

1. **Bootstrap Infra**
   Provision one-time prerequisites first:
   - required GCP APIs
   - Artifact Registry repository
   - Terraform remote state usage

2. **Infra**
   Provision the infrastructure foundation first:
   - Cloud Run, IAM, and monitoring platform resources when running the full infra workflow
   - the Infrastructure workflow can use a placeholder Cloud Run sample image so platform preparation does not depend on CI running first

3. **CI**
   Validate the Python FastAPI application and build the Docker image.
   On `main`, CI can also publish the image to Artifact Registry when GCP repository settings are configured.

4. **CD**
   Deploy a chosen image into the already-provisioned infrastructure using Terraform apply.

The workflows are intentionally split so the delivery path is easier to understand:

- `.github/workflows/bootstrap-infra.yml`
- `.github/workflows/infra.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/cd.yml`

## Resource List

This project provisions:

- Artifact Registry Docker repository
- Cloud Run v2 service
- Dedicated Cloud Run runtime service account
- Cloud Run IAM binding for public invocation when enabled
- Required GCP API enablement
- Cloud Monitoring alert policy for Cloud Run 5xx errors
- Cloud Monitoring alert policy for Cloud Run high latency

This project intentionally does **not** provision:

- Cloud SQL
- GKE
- Compute Engine
- persistent disks
- Redis / Memorystore
- Pub/Sub
- CI/CD infrastructure resources inside GCP

Those are not needed because the API is stateless and request-driven.

## Assumptions and Tradeoffs

- Cloud Run is used because the application is a stateless HTTP container with no persistent storage requirement.
- Artifact Registry is provisioned separately because the platform needs a repository before CI can publish images.
- The workflows are split into bootstrap, infrastructure, CI, and CD to keep the delivery path explicit.
- Public Cloud Run access is configurable and defaults to a simple initial mode, but production environments should restrict access.

## Folder Structure

```text
terraform/
  environments/
    dev/
      main.tf
      variables.tf
      terraform.tfvars.example
      outputs.tf
  modules/
    artifact-registry/
      main.tf
      variables.tf
      outputs.tf
    cloud-run/
      main.tf
      variables.tf
      outputs.tf
    monitoring/
      main.tf
      variables.tf
      outputs.tf
  versions.tf
  README.md
```

## Module Design

### `modules/artifact-registry`

Creates a Docker-format Artifact Registry repository. This is where the `dag-health-api` image is pushed before deployment.

### `modules/cloud-run`

Creates:

- a dedicated service account
- the Cloud Run v2 service
- optional public invoker IAM binding

The Cloud Run module also sets:

- CPU and memory limits
- min/max instances
- request timeout
- container port
- environment variables

### `modules/monitoring`

Creates Cloud Monitoring alert policies for:

- Cloud Run 5xx responses
- Cloud Run request latency above a configurable threshold

Cloud Run automatically publishes metrics such as:

- request count
- request latency
- CPU utilization
- memory utilization
- instance count

Cloud Logging also works automatically for Cloud Run with no extra collector setup. Container stdout/stderr and request logs flow to Google Cloud Logging by default.

## Prerequisites

Before running Terraform, you need:

- a GCP project
- billing enabled on that project
- Terraform `>= 1.6`
- Google Cloud SDK (`gcloud`) installed
- Docker installed
- authenticated GCP credentials with permission to create:
  - Artifact Registry repositories
  - Cloud Run services
  - service accounts
  - monitoring alert policies
  - project service enablement
- a GCS bucket for Terraform remote state if you plan to use the GitHub Actions deployment workflow

Authenticate locally:

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

Important:

- `google_project_service` can enable most required APIs
- the Service Usage API itself must already be usable in the project
- the `dev` environment includes an empty `gcs` backend block so CI can validate with `-backend=false`, while deployment workflows can initialize real remote state using backend config

## Terraform Variables

The dev environment uses these key variables:

- `project_id`
- `region`
- `environment`
- `service_name`
- `image_tag`
- `container_image`
- `allow_unauthenticated`
- `notification_channel_ids`
- `enable_5xx_alert`
- `enable_latency_alert`
- `latency_threshold_ms`

If `container_image` is left `null`, Terraform derives the image from:

- Artifact Registry repository URL
- `service_name`
- `image_tag`

Example image:

```text
REGION-docker.pkg.dev/PROJECT_ID/dag-health-api-dev-repo/dag-health-api:latest
```

## Terraform Init / Plan / Apply

Bootstrap note:

- Artifact Registry must exist before you can push the application image.
- For a brand-new project, the clean flow is:
  1. create the repository first
  2. build and push the image
  3. apply the full stack

From the repository root:

```bash
cd terraform/environments/dev
cp terraform.tfvars.example terraform.tfvars
terraform init \
  -backend-config="bucket=YOUR_TF_STATE_BUCKET" \
  -backend-config="prefix=dag-health-api/dev"
terraform apply -target=module.artifact_registry
```

Then build and push the image, and finish with a full apply:

```bash
terraform plan
terraform apply
```

Or without changing directories:

```bash
terraform -chdir=terraform/environments/dev init \
  -backend-config="bucket=YOUR_TF_STATE_BUCKET" \
  -backend-config="prefix=dag-health-api/dev"
terraform -chdir=terraform/environments/dev apply -target=module.artifact_registry
terraform -chdir=terraform/environments/dev plan
terraform -chdir=terraform/environments/dev apply
```

If you only want local validation and do not want to configure remote state yet, use:

```bash
terraform -chdir=terraform/environments/dev init -backend=false
terraform -chdir=terraform/environments/dev validate
```

GitHub Actions equivalent:

- Bootstrap: run the **Bootstrap Infrastructure** workflow once to create prerequisite APIs and Artifact Registry
- Step 1: run the **Infrastructure** workflow to prepare the platform
- Step 2: run the **CI** workflow to build and publish the artifact
- Step 3: run the **CD** workflow to deploy the artifact

## Docker Build and Push Example

Build the container image from the application root:

```bash
docker build -t dag-health-api:latest .
```

After `terraform apply`, use the Artifact Registry output to tag and push the image:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev

docker tag dag-health-api:latest \
  us-central1-docker.pkg.dev/YOUR_PROJECT_ID/dag-health-api-dev-repo/dag-health-api:latest

docker push \
  us-central1-docker.pkg.dev/YOUR_PROJECT_ID/dag-health-api-dev-repo/dag-health-api:latest
```

If you want Terraform to deploy a specific image directly, set:

```hcl
container_image = "us-central1-docker.pkg.dev/YOUR_PROJECT_ID/dag-health-api-dev-repo/dag-health-api:latest"
```

## How the Cloud Run Service Uses the Image

The Cloud Run service deploys the image provided by `container_image`, or the derived image built from:

- repository URL
- service name
- image tag

The module intentionally overrides the container startup command in Cloud Run so the service listens on the configured Cloud Run port, which defaults to `8080`.

That keeps the infrastructure aligned with Cloud Run runtime expectations even if the image has a different default `CMD`.

## How to Call the Deployed API

After `terraform apply`, get the service URL from output:

```bash
terraform -chdir=terraform/environments/dev output cloud_run_service_url
```

Example request:

```bash
curl -X POST "$(terraform -chdir=terraform/environments/dev output -raw cloud_run_service_url)/evaluate-health" \
  -H "Content-Type: application/json" \
  -d '{
    "components": [
      {"name": "frontend", "health_check_url": "http://frontend/health"},
      {"name": "api-service", "health_check_url": "http://api-service/health"},
      {"name": "database", "health_check_url": "http://database/health"}
    ],
    "dependencies": [
      ["frontend", "api-service"],
      ["api-service", "database"]
    ]
  }'
```

## Security Notes

- Cloud Run uses a **dedicated service account** instead of the default compute identity.
- No broad `Owner` or `Editor` roles are granted by Terraform.
- Public invocation is configurable through `allow_unauthenticated`.
- The default is public for simple initial access and testing.

Production recommendation:

- set `allow_unauthenticated = false`
- front the service with a controlled access layer such as IAM-authenticated callers, API Gateway, or IAP depending on the broader architecture

This Terraform keeps privileges intentionally narrow because the application itself is stateless and does not need extra GCP resource access by default.

## Observability Notes

Cloud Run automatically sends logs to Cloud Logging. That includes:

- request logs
- container stdout
- container stderr

Cloud Run also automatically emits metrics into Cloud Monitoring, including:

- request count
- latency
- CPU utilization
- memory utilization
- instance count

This project adds Cloud Monitoring alert policies for 5xx responses and high request latency on the Cloud Run service. The latency alert defaults to `2000 ms` (2 seconds). Notification channel IDs are optional:

- if provided, alerts can notify email, PagerDuty, Slack integrations, and more
- if omitted, the policy can still be created and wired later

## Runtime Assumptions

- The app is packaged as a single HTTP container.
- The container image already contains the FastAPI application.
- No persistent filesystem or database is required.
- Scale-to-zero is acceptable for the dev environment.
- The service should be reachable over HTTPS from Cloud Run.

## What Is Intentionally Not Included

To keep the design aligned with the actual application and avoid over-engineering, this project does not include:

- a database, because the API is stateless
- VPC connectors, because no private network egress requirement was stated
- load balancers, because Cloud Run already provides the managed HTTPS endpoint
- secrets management, because no secrets were specified for this app
- CI/CD infrastructure resources in Terraform, because the repository uses GitHub Actions workflow files instead

Optional note:

- if this project were extended further, the existing GitHub Actions workflows could be expanded with environment approvals, promotion logic, and deeper deployment verification

## Current Implementation vs Future Scope

Current implementation includes:

- Artifact Registry
- Cloud Run service and service account
- public invoker configuration toggle
- Cloud Monitoring 5xx alert policy
- Cloud Monitoring latency alert policy
- environment-aware variables and outputs
- GitHub workflow alignment for bootstrap, infra, CI, and CD

Future scope could include:

- private networking and VPC connectors
- secrets integration
- stricter production IAM boundaries
- additional alert policies and dashboards
- automated promotion across multiple environments

## Outputs

The dev environment exposes useful outputs, including:

- Cloud Run URL
- Cloud Run service name
- Artifact Registry repository name
- Artifact Registry repository URL
- Cloud Run service account email
- deployed container image
- Cloud Monitoring 5xx alert policy name
- Cloud Monitoring latency alert policy name
