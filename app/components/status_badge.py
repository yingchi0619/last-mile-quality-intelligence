"""Operational status classification and badge helpers."""


def operational_status(otd: float, exception_rate: float, utilization: float) -> str:
    if otd < 0.82 or exception_rate > 0.18 or utilization > 1.05:
        return "At Risk"
    if otd < 0.90 or exception_rate > 0.10 or utilization > 0.95:
        return "Watch"
    return "Healthy"


def status_html(status: str) -> str:
    css = {"Healthy": "green", "Watch": "orange", "At Risk": "red"}.get(status, "blue")
    return f'<span class="badge badge-{css}">{status}</span>'
