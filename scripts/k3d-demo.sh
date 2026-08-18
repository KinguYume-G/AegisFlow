#!/usr/bin/env bash
set -euo pipefail

readonly CLUSTER_NAME="aegisflow-demo"
readonly NAMESPACE="${DEMO_NAMESPACE:-aegisflow-demo}"
readonly RELEASE="${DEMO_RELEASE:-aegisflow}"
readonly SECRET_NAME="${DEMO_SECRET_NAME:-aegisflow-demo-config}"
readonly APP_IMAGE="${AEGISFLOW_DEMO_IMAGE:-aegisflow-core:demo}"
readonly CHART="deploy/helm/aegisflow"
readonly FULLNAME="${RELEASE}-aegisflow"

require_commands() {
  local command_name
  for command_name in docker k3d kubectl helm; do
    command -v "${command_name}" >/dev/null 2>&1 || {
      echo "required command is unavailable: ${command_name}" >&2
      return 1
    }
  done
}

cluster_exists() {
  k3d cluster list --no-headers 2>/dev/null \
    | grep -q "^${CLUSTER_NAME}[[:space:]]"
}

create_runtime_secret() {
  local app_user="aegisflow_demo"
  local app_password="demo-only-not-a-secret"
  local app_database="aegisflow_demo"
  local temporal_user="temporal_demo"
  local temporal_password="temporal-demo-only-not-a-secret"
  local temporal_database="temporal"
  local app_host="${FULLNAME}-postgres"

  kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
  kubectl -n "${NAMESPACE}" create secret generic "${SECRET_NAME}" \
    --from-literal=POSTGRES_USER="${app_user}" \
    --from-literal=POSTGRES_PASSWORD="${app_password}" \
    --from-literal=POSTGRES_DB="${app_database}" \
    --from-literal=DATABASE_URL="postgresql+asyncpg://${app_user}:${app_password}@${app_host}:5432/${app_database}" \
    --from-literal=LANGGRAPH_DATABASE_URL="postgresql://${app_user}:${app_password}@${app_host}:5432/${app_database}" \
    --from-literal=TEMPORAL_POSTGRES_USER="${temporal_user}" \
    --from-literal=TEMPORAL_POSTGRES_PASSWORD="${temporal_password}" \
    --from-literal=TEMPORAL_POSTGRES_DB="${temporal_database}" \
    --dry-run=client -o yaml | kubectl apply -f -
}

up() {
  require_commands
  if ! cluster_exists; then
    k3d cluster create --config deploy/k3d/cluster-config.yaml --wait
  fi
  docker build --target runtime --tag "${APP_IMAGE}" .
  k3d image import "${APP_IMAGE}" --cluster "${CLUSTER_NAME}" --mode direct
  create_runtime_secret
  helm upgrade --install "${RELEASE}" "${CHART}" \
    --namespace "${NAMESPACE}" \
    --set-string existingSecret="${SECRET_NAME}" \
    --set-string core.image.repository="${APP_IMAGE%:*}" \
    --set-string core.image.tag="${APP_IMAGE##*:}"
}

verify() {
  require_commands
  kubectl -n "${NAMESPACE}" rollout status statefulset/"${FULLNAME}-postgres" --timeout=120s
  kubectl -n "${NAMESPACE}" rollout status statefulset/"${FULLNAME}-temporal-postgres" --timeout=120s
  kubectl -n "${NAMESPACE}" rollout status deployment/"${FULLNAME}-redis" --timeout=120s
  kubectl -n "${NAMESPACE}" rollout status deployment/"${FULLNAME}-temporal" --timeout=180s
  kubectl -n "${NAMESPACE}" rollout status deployment/"${FULLNAME}-core" --timeout=120s
  kubectl -n "${NAMESPACE}" rollout status deployment/"${FULLNAME}-worker" --timeout=120s
  kubectl -n "${NAMESPACE}" rollout status deployment/"${FULLNAME}-prometheus" --timeout=120s
  kubectl -n "${NAMESPACE}" rollout status deployment/"${FULLNAME}-grafana" --timeout=120s
  kubectl -n "${NAMESPACE}" run "aegisflow-smoke-${RANDOM}" \
    --image="${APP_IMAGE}" --image-pull-policy=Never \
    --labels=aegisflow.io/access-core=true,aegisflow.io/access-prometheus=true,aegisflow.io/access-grafana=true \
    --restart=Never --rm -i -- \
    python -c "import json,time,urllib.request; base='http://${FULLNAME}-core:8000'; prom='http://${FULLNAME}-prometheus:9090/api/v1/query?query=up%7Bjob%3D%22aegisflow-core%22%7D'; grafana='http://${FULLNAME}-grafana:3000'; deadline=time.time()+60; last=None
while time.time()<deadline:
  try:
    health=json.load(urllib.request.urlopen(base+'/health',timeout=3)); metrics=urllib.request.urlopen(base+'/metrics',timeout=3).read().decode(); result=json.load(urllib.request.urlopen(prom,timeout=3)); grafana_health=json.load(urllib.request.urlopen(grafana+'/api/health',timeout=3)); dashboard=json.load(urllib.request.urlopen(grafana+'/api/dashboards/uid/aegisflow-gate4',timeout=3)); assert health=={'status':'ok','service':'aegisflow-core'}; assert '# HELP' in metrics; assert result['data']['result'][0]['value'][1]=='1'; assert grafana_health['database']=='ok'; assert dashboard['dashboard']['uid']=='aegisflow-gate4'; print('k3d smoke passed'); break
  except Exception as error:
    last=type(error).__name__; time.sleep(2)
else:
  raise RuntimeError('bounded smoke failed: '+str(last))"
}

upgrade_rollback() {
  require_commands
  local base_revision
  base_revision="$(helm history "${RELEASE}" -n "${NAMESPACE}" --max 1 -o json | python -c 'import json,sys; print(json.load(sys.stdin)[-1]["revision"])')"
  helm upgrade "${RELEASE}" "${CHART}" -n "${NAMESPACE}" \
    --reuse-values --set core.replicaCount=2 --wait --timeout 10m
  test "$(kubectl -n "${NAMESPACE}" get deployment "${FULLNAME}-core" -o jsonpath='{.spec.replicas}')" = "2"
  helm rollback "${RELEASE}" "${base_revision}" -n "${NAMESPACE}" --wait --timeout 10m
  test "$(kubectl -n "${NAMESPACE}" get deployment "${FULLNAME}-core" -o jsonpath='{.spec.replicas}')" = "1"
  verify
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      echo "## M5 k3s / Helm evidence"
      echo
      echo "- install, health, metrics, Prometheus scrape, Grafana dashboard: passed"
      echo "- upgrade to two Core replicas: passed"
      echo "- rollback to revision ${base_revision}: passed"
      echo
      echo '```text'
      helm status "${RELEASE}" -n "${NAMESPACE}"
      kubectl get pods -n "${NAMESPACE}" -o wide
      echo '```'
    } >> "${GITHUB_STEP_SUMMARY}"
  fi
}

down() {
  require_commands
  if cluster_exists; then
    k3d cluster delete "${CLUSTER_NAME}"
  fi
}

case "${1:-}" in
  up) up ;;
  verify) verify ;;
  upgrade-rollback) upgrade_rollback ;;
  down) down ;;
  *) echo "usage: $0 {up|verify|upgrade-rollback|down}" >&2; exit 2 ;;
esac
