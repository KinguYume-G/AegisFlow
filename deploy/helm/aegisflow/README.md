# AegisFlow demo chart

This chart installs the modular monolith and its demo dependencies on an ephemeral k3s-compatible cluster. It is not a production HA topology.

The chart never creates credentials. Create an externally managed Secret containing `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `LANGGRAPH_DATABASE_URL`, `TEMPORAL_POSTGRES_USER`, `TEMPORAL_POSTGRES_PASSWORD`, and `TEMPORAL_POSTGRES_DB`, then pass its name:

```bash
helm upgrade --install aegisflow ./deploy/helm/aegisflow \
  --namespace aegisflow-demo --create-namespace \
  --set existingSecret=aegisflow-demo-config
```

Use `scripts/k3d-demo.sh` for the complete ephemeral install, verification, upgrade, rollback, and teardown workflow. Never place a real credential in a values file or command committed to the repository.
