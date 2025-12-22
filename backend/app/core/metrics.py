from __future__ import annotations

import time
from typing import Callable

from fastapi import APIRouter, Request, Response

try:
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest  # type: ignore

    _PROM_AVAILABLE = True
except Exception:  # pragma: no cover
    _PROM_AVAILABLE = False

    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"

    class _NoopMetric:
        def labels(self, **_labels):  # noqa: ANN003
            return self

        def inc(self, _amount: float = 1.0) -> None:
            return None

        def observe(self, _value: float) -> None:
            return None

    def Counter(*_args, **_kwargs):  # noqa: N802, ANN001, ANN002
        return _NoopMetric()

    def Histogram(*_args, **_kwargs):  # noqa: N802, ANN001, ANN002
        return _NoopMetric()

    def generate_latest() -> bytes:  # noqa: ANN001
        return b""


router = APIRouter(tags=["metrics"])


http_requests_total = Counter(
    "todiscope_http_requests_total",
    "Total HTTP requests.",
    labelnames=("method", "path", "status"),
)

http_request_duration_seconds = Histogram(
    "todiscope_http_request_duration_seconds",
    "HTTP request duration seconds.",
    labelnames=("method", "path"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

engine_exports_total = Counter(
    "todiscope_engine_exports_total",
    "Engine export attempts and outcomes.",
    labelnames=("engine_id", "format", "view_type", "status"),
)

engine_runs_total = Counter(
    "todiscope_engine_runs_total",
    "Engine run attempts and outcomes.",
    labelnames=("engine_id", "status"),
)

engine_run_duration_seconds = Histogram(
    "todiscope_engine_run_duration_seconds",
    "Engine run duration seconds.",
    labelnames=("engine_id", "status"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)

engine_model_duration_seconds = Histogram(
    "todiscope_engine_model_duration_seconds",
    "Engine modeling duration seconds.",
    labelnames=("engine_id",),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

engine_persistence_duration_seconds = Histogram(
    "todiscope_engine_persistence_duration_seconds",
    "Engine persistence duration seconds.",
    labelnames=("engine_id", "stage"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

engine_errors_total = Counter(
    "todiscope_engine_errors_total",
    "Engine run errors by type.",
    labelnames=("engine_id", "error_type"),
)


@router.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def metrics_middleware() -> Callable:
    async def _middleware(request: Request, call_next: Callable) -> Response:
        method = request.method
        path = request.url.path
        start = time.perf_counter()
        status = "500"
        try:
            resp = await call_next(request)
            status = str(resp.status_code)
            return resp
        finally:
            http_requests_total.labels(method=method, path=path, status=status).inc()
            http_request_duration_seconds.labels(method=method, path=path).observe(time.perf_counter() - start)

    return _middleware
