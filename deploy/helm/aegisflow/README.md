# AegisFlow demo chart

This chart installs the Core control plane and its M5 demo dependencies on an ephemeral k3s-compatible cluster. It is not a production HA topology.

The Temporal Worker is disabled by default. The current DeliveryPack Worker requires
the governed Sandbox Broker, model routing and workspace contract that AF-R11 will
package for Kubernetes. Enabling a partial Worker here would create a crash-looping
pod and falsely imply that the complete execution plane was deployed. Use the local
Compose profile for the current end-to-end Agent loop; do not set `worker.enabled`
until those dependencies are supplied by the AF-R11 deployment slice.

The chart never creates credentials. Create an externally managed Secret containing `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`, `LANGGRAPH_DATABASE_URL`, `TEMPORAL_POSTGRES_USER`, `TEMPORAL_POSTGRES_PASSWORD`, and `TEMPORAL_POSTGRES_DB`, then pass its name:

```bash
helm upgrade --install aegisflow ./deploy/helm/aegisflow \
  --namespace aegisflow-demo --create-namespace \
  --set existingSecret=aegisflow-demo-config
```

Use `scripts/k3d-demo.sh` for the complete ephemeral install, verification, upgrade, rollback, and teardown workflow. Never place a real credential in a values file or command committed to the repository.
