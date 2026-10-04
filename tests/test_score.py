from fastapi.testclient import TestClient
from clv.main import app

client = TestClient(app)


def test_high_and_low():
    assert client.post("/score", json={'monthly_revenue': 40, 'tenure_months': 24, 'churn_prob': 0.05}).json()["label"]
    high = client.post("/score", json={'monthly_revenue': 40, 'tenure_months': 24, 'churn_prob': 0.05}).json()
    low = client.post("/score", json={'monthly_revenue': 8, 'tenure_months': 1, 'churn_prob': 0.6}).json()
    assert high["label"] != low["label"]
    assert high["score"] > low["score"]


def test_missing_is_refused():
    body = dict({'monthly_revenue': 40, 'tenure_months': 24, 'churn_prob': 0.05})
    body.pop("monthly_revenue")
    assert client.post("/score", json=body).status_code == 422
