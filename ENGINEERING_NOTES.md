# Engineering Notes

## AI Tool Usage Disclosure

AI assistance was used during this project to help draft and refine:

- FastAPI application structure
- Terraform module structure
- GitHub Actions workflow structure
- Docker and infrastructure supporting files
- documentation drafts

AI assistance was used as a drafting and iteration tool, not as an authoritative source of truth.

The final project was reviewed, corrected, and integrated so the repository reflects a consistent implementation rather than raw generated output.

## Where AI-Assisted Output Was Used

AI-assisted output contributed to:

- application module scaffolding
- request/response model layout
- graph evaluation and health aggregation structure
- observability additions
- Dockerfile and Terraform boilerplate
- CI/CD workflow scaffolding
- README and architecture documentation drafts

## Validation and Refinement Performed

The generated output was validated and refined through multiple review passes:

- Python test suite was run and fixed until passing
- Terraform configuration was formatted and validated
- Docker image was built and container startup was verified
- workflow files were restructured to separate bootstrap, infrastructure, CI, and CD concerns
- documentation was simplified and aligned across the repository
- package configuration was corrected after Terraform files introduced a Python packaging discovery issue
- observability behavior was tested and adjusted after readiness behavior surfaced in tests

## Corrections Applied to AI Output

The generated output was not accepted unchanged. Notable corrections and constraints included:

- separating BFS traversal from reverse-topological evaluation so dependency propagation remained correct
- splitting mixed CI/CD workflow logic into clearer workflow boundaries
- correcting Terraform workflow structure so infrastructure bootstrap and deployment were not conflated
- tightening packaging configuration to avoid accidental inclusion of non-Python directories
- changing Docker startup behavior to direct exec form instead of shell-wrapped startup
- making infrastructure documentation and naming more consistent across environments
- simplifying Markdown documentation and removing review-oriented wording

## Evidence of Review

The repository contains concrete signs that generated output was reviewed and integrated thoughtfully:

- app code, infrastructure, workflows, and docs use consistent naming around `dag-health-api`
- environment-aware Terraform naming is consistent across modules and examples
- operational endpoints, metrics, logging, and Cloud Run configuration align with each other
- delivery workflows now reflect a clear sequence:
  - bootstrap infrastructure
  - infrastructure preparation
  - CI artifact build
  - CD artifact deployment
- docs distinguish current implementation from future scope

## Coherence of the Final Solution

The final project is coherent end to end:

- the application is Dockerized
- Terraform provisions the target GCP runtime for that container
- workflows reflect bootstrap, platform, build, and deploy steps
- observability exists both in the app and in the Cloud Run/Monitoring design
- documentation explains how to run, test, deploy, and extend the system

## Summary

AI tools were used to accelerate drafting and iteration, but the repository was refined through validation, correction, restructuring, and documentation cleanup so that the final result reads as a reviewed engineering solution rather than unfiltered generated output.
