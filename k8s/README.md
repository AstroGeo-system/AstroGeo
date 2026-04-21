# AstroGeo Kubernetes Stack

This folder includes base manifests for:

- `astrogeo-api` (FastAPI backend)
- `prometheus` (metrics collection)
- `grafana` (dashboards)
- `mlflow` (experiment tracking)

## 1) Create namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

## 2) Create secrets

Create one secret with all runtime keys:

```bash
kubectl -n astrogeo create secret generic astrogeo-secrets \
  --from-literal=OPENAI_API_KEY="..." \
  --from-literal=NASA_API_KEY="..." \
  --from-literal=N2YO_API_KEY="..." \
  --from-literal=COPERNICUS_CLIENT_ID="..." \
  --from-literal=COPERNICUS_CLIENT_SECRET="..." \
  --from-literal=DB_HOST="..." \
  --from-literal=DB_PORT="5432" \
  --from-literal=DB_NAME="..." \
  --from-literal=DB_USER="..." \
  --from-literal=DB_PASSWORD="..." \
  --from-literal=NEO4J_URI="..." \
  --from-literal=NEO4J_USERNAME="..." \
  --from-literal=NEO4J_PASSWORD="..." \
  --from-literal=NEO4J_DATABASE="..." \
  --from-literal=GRAFANA_ADMIN_PASSWORD="admin"
```

## 3) Apply manifests

```bash
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/prometheus.yaml
kubectl apply -f k8s/grafana.yaml
kubectl apply -f k8s/mlflow.yaml
```

## 4) Access services locally (port-forward)

```bash
kubectl -n astrogeo port-forward svc/astrogeo-api 8000:8000
kubectl -n astrogeo port-forward svc/prometheus 9090:9090
kubectl -n astrogeo port-forward svc/grafana 3000:3000
kubectl -n astrogeo port-forward svc/mlflow 5001:5000
```

## Notes

- `api-deployment.yaml` uses image `ghcr.io/astrogeo-system/astrogeo-backend:latest` as placeholder.
  Replace this with your actual published backend image.
- `mlflow` currently uses `emptyDir` storage (ephemeral). For production, switch to PVC/object storage.
- Grafana comes with a preconfigured Prometheus datasource in k8s manifest.

