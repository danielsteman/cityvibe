# Infrastructure

This directory contains infrastructure as code (IaC) configurations and deployment scripts for City Vibe.

## Structure

- **`kubernetes/`** - Kubernetes manifests for container orchestration
  - Deployments for all services (mcp-server, api, workers, scheduler)
  - Services, Ingress, and networking configurations
  - ConfigMaps and Secrets management
  - StatefulSets for stateful services (if needed)

- **`terraform/`** - Terraform configurations for cloud infrastructure (optional)
  - Cloud provider resources (AWS/GCP/Azure)
  - VPC, subnets, security groups
  - Managed database instances (RDS, Cloud SQL, etc.)
  - Load balancers and networking components

- **`scripts/`** - Deployment and utility scripts
  - `deploy.sh` - Automated deployment scripts
  - `setup.sh` - Initial infrastructure setup
  - `backup.sh` - Database backup automation
  - `health-check.sh` - Service health monitoring

## Usage

### Kubernetes Deployment

```bash
# Apply all Kubernetes manifests
kubectl apply -f kubernetes/

# Deploy specific service
kubectl apply -f kubernetes/api/
```

### Terraform (if used)

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Scripts

```bash
# Run deployment script
./scripts/deploy.sh

# Setup infrastructure
./scripts/setup.sh
```
