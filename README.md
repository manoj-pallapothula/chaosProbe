# ChaosProbe

A chaos engineering framework built from scratch. It breaks your services on purpose — controlled faults, real SLO checks, automatic rollback — then tells you whether your system held up.


## Why this exists

Production failures are unpredictable. The only way to know how your system behaves under stress is to stress it yourself, on your own terms, before users find out the hard way.

Netflix has Chaos Monkey. Google runs DiRT exercises. ChaosProbe is that idea implemented as a real, runnable tool — fault injection engine, Prometheus-backed SLO monitoring, auto-rollback, REST API, and a CLI that gives you readable output.


## What it does

Load experiment YAML
↓
Check system is healthy before starting
↓
Inject a fault (CPU spike / latency / memory / process kill)
↓
Scrape Prometheus every N seconds — error rate, p99 latency, availability
↓
SLO breached? Roll back immediately
↓
Remove fault, check system recovered
↓
Verdict: PASSED / FAILED / ABORTED + full event timeline


## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.13 |
| API | FastAPI + Uvicorn |
| Database | PostgreSQL + SQLAlchemy |
| Metrics | Prometheus + Grafana |
| Containers | Docker + Docker Compose |
| CLI | Typer + Rich |
| Tests | pytest — 55 tests, 90% coverage |


## Getting started

```bash
git clone https://github.com/manoj-pallapothula/chaosProbe.git
cd chaosProbe
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && pip install -e .
```

Start everything:

```bash
make up
```

Run your first experiment:

```bash
chaosctl run --config configs/experiments/cpu_stress_experiment.yaml
```


## CLI

```bash
chaosctl run --config configs/experiments/cpu_stress_experiment.yaml
chaosctl list
chaosctl report --id <experiment-id>
chaosctl status
```


## Experiment config

```yaml
name: "CPU Stress — Target API"

steady_state:
  checks:
    - name: "Error rate nominal"
      type: metric
      metric: "target_error_rate"
      threshold: 0.01
      operator: "<"

fault:
  type: cpu_stress
  target: target-api
  duration_seconds: 60
  params:
    cpu_load_percent: 80
    workers: 2

slo:
  error_rate_percent: 5.0
  latency_p99_ms: 500
  availability_percent: 95.0

rollback:
  on_slo_breach: true
  grace_period_seconds: 10
```

## Fault types

| Fault | What it does |
|-------|-------------|
| `cpu_stress` | Pegs CPU at X% using stress-ng or a Python fallback |
| `memory_pressure` | Allocates and holds RAM via mmap |
| `latency_injection` | Adds delay via HTTP endpoint or tc/netem |
| `process_kill` | Kills by name, PID, or Docker container |


## API

| Method | Endpoint | What it does |
|--------|----------|-------------|
| POST | `/api/v1/experiments/run` | Run an experiment |
| GET | `/api/v1/experiments` | List all runs |
| GET | `/api/v1/experiments/{id}` | Get one run |
| DELETE | `/api/v1/experiments/{id}` | Delete a run |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

Docs at `http://localhost:8080/docs` when running locally.


## Running tests

```bash
pytest
pytest --cov=chaosProbe
```


## Project layout

chaosProbe/
├── chaosProbe/
│   ├── faults/       # fault injectors
│   ├── engine/       # orchestrator + experiment model
│   ├── monitoring/   # SLO monitor + Prometheus client
│   ├── api/          # FastAPI server
│   ├── cli/          # chaosctl commands
│   └── utils/        # config, logger
├── tests/            # 55 tests, 90% coverage
├── configs/          # experiment YAML files
└── docker/           # docker-compose + target services

## Dashboards

| Service | URL |
|---------|-----|
| ChaosProbe API | http://localhost:8080 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin/admin) |


**Manoj Kumar Pallapothula** 
[LinkedIn](https://linkedin.com/in/manojkumarpallapothula)
