REQUIRED = ("monthly_revenue", "tenure_months", "churn_prob",)
WEIGHTS = {"monthly_revenue": 12.0, "tenure_months": 5.0, "churn_prob": -80.0}
INTERCEPT = 20.0
THRESHOLD = 100.0


class InputError(ValueError):
    pass


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
