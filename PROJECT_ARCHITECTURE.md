# customer-lifetime-value-predictor — project architecture

[README](README.md) · [Interview questions and answers](INTERVIEW_QA.md)

## Purpose and scope

Score monthly revenue, tenure, and churn probability into a dollar-like score. Missing features are refused.

This document describes files and symbols in this checkout. Deployment templates and statements in the original overview are distinguished from a verified running environment.

## Component diagram

```mermaid
flowchart LR
    M0["src/clv/__init__.py"]
    M1["src/clv/main.py"]
    M2["src/clv/ops.py"]
    M3["src/clv/score.py"]
    M1 -->|imports| M2
    M1 -->|imports| M3
```

For Python repositories, arrows show resolved local imports, not network calls or deployment order. Otherwise the diagram is a repository component map; containment arrows do not assert runtime integration.

## Components and responsibilities

| Component | Responsibility |
| --- | --- |
| [`src/clv/main.py`](src/clv/main.py) | HTTP handlers: `GET /healthz`, `POST /score` |
| [`src/clv/ops.py`](src/clv/ops.py) | HTTP handlers: `GET /readyz`, `POST /workspaces`, `GET /workspaces`, `POST /workspaces/{workspace_id}/jobs`, `GET /jobs/{job_id}` |
| [`src/clv/score.py`](src/clv/score.py) | Functions: `score` |
| [`requirements.txt`](requirements.txt) | Implementation or supporting configuration |
| [`src/clv/__init__.py`](src/clv/__init__.py) | Implementation or supporting configuration |
| [`Dockerfile`](Dockerfile) | Container build/service configuration |
| [`Makefile`](Makefile) | Implementation or supporting configuration |
| [`docker-compose.yml`](docker-compose.yml) | Container build/service configuration |
| [`tests/test_ops.py`](tests/test_ops.py) | Executable checks and regression examples |
| [`tests/test_score.py`](tests/test_score.py) | Executable checks and regression examples |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | GitHub Actions job definitions |
| [`README.md`](README.md) | Project explanations or operating notes |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Project explanations or operating notes |

## Existing design and operating guides

These checked-in guides provide the project’s detailed design, operational context, or deployment view:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Request interface

| Method and path | Handler | Source |
| --- | --- | --- |
| `GET /healthz` | `healthz` | [`src/clv/main.py`](src/clv/main.py#L10) |
| `POST /score` | `post_score` | [`src/clv/main.py`](src/clv/main.py#L15) |
| `GET /readyz` | `readyz` | [`src/clv/ops.py`](src/clv/ops.py#L44) |
| `POST /workspaces` | `create_workspace` | [`src/clv/ops.py`](src/clv/ops.py#L49) |
| `GET /workspaces` | `list_workspaces` | [`src/clv/ops.py`](src/clv/ops.py#L66) |
| `POST /workspaces/{workspace_id}/jobs` | `create_job` | [`src/clv/ops.py`](src/clv/ops.py#L73) |
| `GET /jobs/{job_id}` | `get_job` | [`src/clv/ops.py`](src/clv/ops.py#L96) |
| `POST /jobs/{job_id}/approve` | `approve_job` | [`src/clv/ops.py`](src/clv/ops.py#L105) |
| `GET /audit` | `audit` | [`src/clv/ops.py`](src/clv/ops.py#L122) |
| `GET /metrics` | `metrics` | [`src/clv/ops.py`](src/clv/ops.py#L138) |

The table lists literal route decorators found in the inspected Python modules. Router prefixes and middleware can add behavior; check the linked handler and application setup before calling an endpoint.

## Implementation walkthrough

### `score(body)`

Source: [`src/clv/score.py`](src/clv/score.py#L11).

Calls visible in this function: `', '.join`, `InputError`, `WEIGHTS.items`, `isinstance`, `parts.append`, `round`.

```python
def score(body):
    missing = [name for name in REQUIRED if name not in body]
    if missing:
        raise InputError("missing " + ", ".join(missing))
    total = INTERCEPT
    parts = []
    for name, weight in WEIGHTS.items():
        value = body[name]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise InputError(f"{name} must be a number")
        contrib = weight * value
        total += contrib
        parts.append({"feature": name, "contribution": round(contrib, 4)})
    label = "retain" if total >= THRESHOLD else "watch"
    return {"score": round(total, 4), "label": label, "threshold": THRESHOLD, "parts": parts}
```

## Validation and failure paths

| Explicit exception | Source |
| --- | --- |
| `HTTPException(status_code=422, detail=str(exc))` | [`src/clv/main.py`](src/clv/main.py#L19) |
| `HTTPException(status_code=404, detail='workspace not found')` | [`src/clv/ops.py`](src/clv/ops.py#L77) |
| `HTTPException(status_code=404, detail='job not found')` | [`src/clv/ops.py`](src/clv/ops.py#L100) |
| `HTTPException(status_code=404, detail='job not found')` | [`src/clv/ops.py`](src/clv/ops.py#L109) |
| `HTTPException(status_code=403, detail='production apply is disabled in this lab')` | [`src/clv/ops.py`](src/clv/ops.py#L113) |
| `InputError('missing ' + ', '.join(missing))` | [`src/clv/score.py`](src/clv/score.py#L14) |
| `InputError(f'{name} must be a number')` | [`src/clv/score.py`](src/clv/score.py#L20) |

These are explicit exceptions in the inspected source, rather than a claim that every failure is handled. Follow the calling handler to see whether the exception becomes an HTTP response or propagates.

## Data and state

- [`src/clv/ops.py`](src/clv/ops.py) defines module-level containers: `_WORKSPACES`, `_JOBS`, `_AUDIT`, `_METRICS`.
- [`src/clv/score.py`](src/clv/score.py) defines module-level containers: `WEIGHTS`.

Module-level dictionaries/lists live in a Python process. They can be fixtures or mutable state; inspect writes before treating them as persistent storage. A production extension would need to define persistence and concurrency behavior explicitly.

## Data flow and design decisions

### What is the input-to-output contract of `score`

In [`src/clv/score.py`](src/clv/score.py#L11), `score(body)` receives the inputs. The function computes these intermediate values:

- `missing = [name for name in REQUIRED if name not in body]`
- `total = INTERCEPT`
- `parts = []`
- `label = 'retain' if total >= THRESHOLD else 'watch'`

Its result is defined by:

- `{'score': round(total, 4), 'label': label, 'threshold': THRESHOLD, 'parts': parts}`

### Which decision rules or boundary conditions should an interviewer challenge

The implementation in [`src/clv/score.py`](src/clv/score.py#L11) branches on:

- `missing`
- `not isinstance(value, (int, float)) or isinstance(value, bool)`

A useful extension is a table-driven test that covers each condition just below, at, and above its boundary where applicable. These expressions are the current rules; changing them changes behavior and should be justified by the project’s acceptance criteria.

### What does the operations plane add, and where is its limit

[`src/clv/ops.py`](src/clv/ops.py) declares `GET /readyz`, `POST /workspaces`, `GET /workspaces`, `POST /workspaces/{workspace_id}/jobs`, `GET /jobs/{job_id}`, `POST /jobs/{job_id}/approve`, `GET /audit`, `GET /metrics`. Inspect the application’s `include_router` call for its URL prefix.

Its state containers are `_WORKSPACES`, `_JOBS`, `_AUDIT`, `_METRICS`. The job-approval handler defines whether a target is accepted or refused; check that branch and the associated tests instead of treating a recorded job as a successful infrastructure apply.

## Setup and verification

The following commands are derived from the checked-in dependency/test contracts. Execute them from the repository root; the block prepares a local environment, not a cloud deployment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Python dependencies: [`requirements.txt`](requirements.txt).

Test entry points: [`tests/test_ops.py`](tests/test_ops.py), [`tests/test_score.py`](tests/test_score.py).

Automation definitions: [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Read their triggers and job steps to determine what CI actually runs.

## Operating boundaries and design review

Before turning this checkout into a customer deployment, establish the input contract, data ownership, access controls, failure response, evaluation criteria, and rollback owner. Repository fixtures and unit tests demonstrate local behavior; they do not establish throughput, uptime, compliance, or business impact.

A useful architecture review starts with the linked implementation: identify where input enters, where a decision is made, which state can change, and which external dependency can fail. Add a deployment view only for infrastructure that is actually configured and exercised.
