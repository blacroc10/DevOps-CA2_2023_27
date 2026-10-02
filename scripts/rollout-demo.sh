#!/usr/bin/env bash
# Rolling update, failed release, and rollback for the TruthGraph API.
set -u
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
export PATH="$HOME/.local/bin:$PATH"
NS=truthgraph

echo "===== api pods before rollout ====="
kubectl -n "$NS" get pods -l app=api -o custom-columns=NAME:.metadata.name,START:.status.startTime,RESTARTS:.status.containerStatuses[0].restartCount

echo "===== start traffic against api ====="
kubectl -n "$NS" delete pod traffic --ignore-not-found --wait=true >/dev/null
kubectl -n "$NS" run traffic \
  --image=truthgraph-api:v1 \
  --image-pull-policy=IfNotPresent \
  --restart=Never \
  --command -- python -c '
import time, urllib.request
ok = fail = 0
end = time.time() + 45
while time.time() < end:
    try:
        urllib.request.urlopen("http://api.truthgraph.svc.cluster.local:8000/health", timeout=2)
        ok += 1
    except Exception:
        fail += 1
    time.sleep(0.05)
print("ok=%s fail=%s" % (ok, fail), flush=True)
'
kubectl -n "$NS" wait --for=condition=Ready pod/traffic --timeout=60s || true

echo "===== roll api v1 -> v2 ====="
kubectl -n "$NS" patch deployment api --type=json -p='[{"op":"replace","path":"/spec/template/spec/containers/0/image","value":"truthgraph-api:v2"},{"op":"replace","path":"/spec/template/spec/containers/0/env/0/value","value":"v2"}]'
kubectl -n "$NS" rollout status deployment/api --timeout=180s
kubectl -n "$NS" rollout history deployment/api
echo "===== api version ====="
kubectl -n "$NS" exec deploy/api -- python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/version", timeout=5).read().decode())'

echo "===== traffic result ====="
kubectl -n "$NS" logs -f pod/traffic || true

echo "===== bad v3 (readiness fails) ====="
kubectl -n "$NS" set env deployment/api APP_VERSION=v3 FAIL_READY=1
set +e
kubectl -n "$NS" rollout status deployment/api --timeout=40s
echo "rollout_status_exit=$?"
set -e
kubectl -n "$NS" get pods -l app=api -o wide
echo "===== service still answers on the previous pods ====="
kubectl -n "$NS" exec deploy/neo4j -- wget -qO- http://api.truthgraph.svc.cluster.local:8000/version
echo

echo "===== rollback ====="
kubectl -n "$NS" rollout undo deployment/api
kubectl -n "$NS" rollout status deployment/api --timeout=180s
kubectl -n "$NS" rollout history deployment/api
kubectl -n "$NS" exec deploy/api -- python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/version", timeout=5).read().decode()); print(urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5).read().decode())'
kubectl -n "$NS" get pods -o wide
