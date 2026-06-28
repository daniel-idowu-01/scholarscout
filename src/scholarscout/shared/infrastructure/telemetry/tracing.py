"""
OpenTelemetry tracing setup.

Configures the OTel SDK once at startup. Every FastAPI request,
SQLAlchemy query, Redis call, and HTTP client call is automatically
instrumented. Background Celery tasks add trace context via headers.
"""

from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

logger = logging.getLogger(__name__)


def configure_tracing(
    service_name: str,
    otlp_endpoint: str | None,
    sample_rate: float = 0.1,
    environment: str = "development",
) -> TracerProvider:
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "0.1.0",
            "deployment.environment": environment,
        }
    )

    sampler = ParentBased(root=TraceIdRatioBased(sample_rate))
    provider = TracerProvider(resource=resource, sampler=sampler)

    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info("OTel traces → %s (sample_rate=%.2f)", otlp_endpoint, sample_rate)
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("OTel traces → stdout (dev mode)")

    trace.set_tracer_provider(provider)
    return provider


def instrument_fastapi(app: object) -> None:
    FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]


def instrument_sqlalchemy(engine: object) -> None:
    SQLAlchemyInstrumentor().instrument(engine=engine, enable_commenter=True)


def instrument_redis() -> None:
    RedisInstrumentor().instrument()


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
