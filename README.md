# DevOps CA-II: TruthGraph

[![truthgraph-ci-cd](https://github.com/aditisharmas11/DevOps-CA2_2023_27/actions/workflows/truthgraph-ci-cd.yml/badge.svg)](https://github.com/aditisharmas11/DevOps-CA2_2023_27/actions/workflows/truthgraph-ci-cd.yml)

Deployment, configuration, Kubernetes, and monitoring for [TruthGraph](https://github.com/dhootraghav/TruthGraph), a claim-verification API. The service in this repo is that backend, plus a `/metrics` endpoint for Prometheus. Groq and Tavily keys are not required for the pipeline: tests mock those calls, and the cluster smoke test uses `/health`, which only needs Neo4j.

## What is in the cluster

One kind cluster, `truthgraph-ca2`, two namespaces:

| Namespace | Workload |
| --- | --- |
| `truthgraph` | API (`truthgraph-api`) and Neo4j 5 |
| `monitoring` | kube-prometheus-stack, trimmed |

The API talks to Neo4j at `bolt://neo4j.truthgraph.svc.cluster.local:7687`. The demo password is the same one as the upstream Compose file (`neo4j` / `password`). It is a lab secret, stored in `k8s/neo4j.yaml`.

## Step 1 — Deployment strategy

GitHub Actions workflow: `.github/workflows/truthgraph-ci-cd.yml`.

Push to `main` runs tests, pushes the image to GHCR, and deploys it on a kind cluster in the runner. A pull request runs the tests and the image build, and it does not push or deploy. If the deploy smoke test fails, the job runs `kubectl rollout undo`.

Diagram: `docs/diagrams/pipeline.mmd` and `docs/PIPELINE.md`.

## Step 2 — Configuration management

Ansible, against a container, not against the host:

```bash
sudo docker run -d --name ca2-ansible-truthgraph ubuntu:24.04 sleep infinity
sudo docker exec ca2-ansible-truthgraph apt-get update
sudo docker exec ca2-ansible-truthgraph apt-get install -y python3 ansible python3-apt
sudo docker cp ansible ca2-ansible-truthgraph:/work/ansible
sudo docker cp service ca2-ansible-truthgraph:/work/service
sudo docker exec -w /work/ansible ca2-ansible-truthgraph ansible-playbook -i inventory.ini playbook.yml --check
sudo docker exec -w /work/ansible ca2-ansible-truthgraph ansible-playbook -i inventory.ini playbook.yml
sudo docker exec -w /work/ansible ca2-ansible-truthgraph ansible-playbook -i inventory.ini playbook.yml
```

The playbook installs packages, creates the `truthsvc` user, writes `/etc/truthgraph/api/app.conf`, and copies the application. The second apply should report `changed=0`.

## Step 3 — Containerization and Kubernetes

```bash
export PATH="$HOME/.local/bin:$PATH"
export KUBECONFIG="$HOME/.kube/config"

docker build -t truthgraph-api:v1 service
docker tag truthgraph-api:v1 truthgraph-api:v2
docker pull neo4j:5-community

kind create cluster --name truthgraph-ca2 --image kindest/node:v1.37.0 --config cluster/kind-config.yaml
kind load docker-image truthgraph-api:v1 truthgraph-api:v2 neo4j:5-community --name truthgraph-ca2
kubectl apply -f k8s/namespace.yaml -f k8s/neo4j.yaml -f k8s/api.yaml
kubectl -n truthgraph rollout status deployment/neo4j --timeout=240s
kubectl -n truthgraph rollout status deployment/api --timeout=240s
```

Rolling update and rollback: `scripts/rollout-demo.sh`. v2 changes `APP_VERSION`. v3 sets `FAIL_READY=1`, so the new pods never become ready and the Service keeps the previous pods. `kubectl rollout undo` returns the Deployment to v2.

## Step 4 — Monitoring

The API exposes Prometheus metrics on `GET /metrics` (`http_requests_total`, `http_request_duration_seconds`). `GET /error` returns 500 so the error-rate panel has something to show.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --version 91.8.2 --namespace monitoring --create-namespace \
  -f monitoring/values.yaml --timeout 12m --wait
kubectl apply -f monitoring/servicemonitor.yaml
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -k monitoring/
```

`values.yaml` turns alertmanager off, turns persistence off, and sets low memory requests because this VM has 7.5 GiB.

```bash
kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80
kubectl -n truthgraph port-forward svc/api 18000:8000
COUNT=40 scripts/load.sh http://127.0.0.1:18000
```

Grafana admin user is `admin`. Read the password when you need it:

```bash
kubectl -n monitoring get secret monitoring-grafana -o jsonpath='{.data.admin-password}' | base64 -d; echo
```

Dashboard: **TruthGraph API** (uptime, latency, error rate). Time range: last 15 minutes.

## Evidence from this machine

`docs/evidence/ansible.txt` is the playbook check, the first apply, and the second apply (`changed=0`). `docs/evidence/rollout.txt` is the v1 to v2 rolling update (`ok=804 fail=0`), the failed v3 readiness gate, and the rollback to v2. `screenshots/grafana-truthgraph.png` is the TruthGraph API dashboard after that run: scrape up, two ready replicas, error ratio, request rate, latency, and per-pod uptime.

Those commands were applied to the kind cluster already named `ca2` on this host, because that cluster already had the trimmed Prometheus stack. The create-cluster commands above are for a clean machine.

## Tests

```bash
python3 -m venv .venv
.venv/bin/pip install -r service/requirements.txt
(cd service && ../.venv/bin/pytest -q)
```

The image uses Python 3.11. CI uses Python 3.11 as well.
