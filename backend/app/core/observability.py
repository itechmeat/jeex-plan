"""OpenTelemetry observability helpers with optional instrumentation."""

from fastapi import FastAPI

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class _NoOpSpan:
    """Span placeholder used when observability is disabled."""

    def __enter__(self) -> "_NoOpSpan":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def set_attribute(self, *_: object, **__: object) -> None:
        return None

    def add_event(self, *_: object, **__: object) -> None:
        return None

    def record_exception(self, *_: object, **__: object) -> None:
        return None

    def end(self) -> None:
        return None


class _NoOpTracer:
    """Tracer facade that returns no-op spans."""

    def start_span(self, *_: object, **__: object) -> _NoOpSpan:
        return _NoOpSpan()


class _NoOpCounter:
    """Counter facade that ignores measurements."""

    def add(self, *_: object, **__: object) -> None:
        return None


class _NoOpHistogram:
    """Histogram facade that ignores measurements."""

    def record(self, *_: object, **__: object) -> None:
        return None


class _NoOpUpDownCounter:
    """Up-down counter facade that ignores measurements."""

    def add(self, *_: object, **__: object) -> None:
        return None


class _NoOpMeter:
    """Meter facade that supplies no-op instruments."""

    def create_counter(self, *_: object, **__: object) -> _NoOpCounter:
        return _NoOpCounter()

    def create_histogram(self, *_: object, **__: object) -> _NoOpHistogram:
        return _NoOpHistogram()

    def create_up_down_counter(self, *_: object, **__: object) -> _NoOpUpDownCounter:
        return _NoOpUpDownCounter()


NOOP_TRACER = _NoOpTracer()
NOOP_METER = _NoOpMeter()


def _noop_setup_observability(_: FastAPI) -> None:
    """Skip instrumentation when observability is disabled."""
    logger.debug("Observability disabled; instrumentation skipped")


def _noop_get_tracer(_: str | None = None) -> _NoOpTracer:
    return NOOP_TRACER


def _noop_get_meter(_: str | None = None) -> _NoOpMeter:
    return NOOP_METER


NOOP_SETUP_OBSERVABILITY = _noop_setup_observability
NOOP_GET_TRACER = _noop_get_tracer
NOOP_GET_METER = _noop_get_meter


if settings.ENABLE_OBSERVABILITY:
    try:
        from opentelemetry import metrics, trace
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import (
            ConsoleMetricExporter,
            PeriodicExportingMetricReader,
        )
        from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )

    except ImportError as exc:  # pragma: no cover - fallback path
        logger.warning(
            "OpenTelemetry packages unavailable (%s); using no-op observability",
            exc,
        )
        setup_observability = NOOP_SETUP_OBSERVABILITY
        get_tracer = NOOP_GET_TRACER
        get_meter = NOOP_GET_METER

    else:

        def setup_observability(app: FastAPI) -> None:
            """Configure OpenTelemetry instrumentation for the FastAPI app."""
            try:
                resource = Resource.create(
                    {
                        SERVICE_NAME: settings.APP_NAME,
                        SERVICE_VERSION: "1.0.0",
                        "environment": settings.ENVIRONMENT,
                    }
                )

                tracer_provider = TracerProvider(resource=resource)

                if settings.OTLP_ENDPOINT:
                    otlp_exporter = OTLPSpanExporter(
                        endpoint=f"{settings.OTLP_ENDPOINT}/v1/traces"
                    )
                    span_processor = BatchSpanProcessor(otlp_exporter)
                else:
                    console_exporter = ConsoleSpanExporter()
                    span_processor = BatchSpanProcessor(console_exporter)

                tracer_provider.add_span_processor(span_processor)
                trace.set_tracer_provider(tracer_provider)

                metric_exporter = (
                    OTLPMetricExporter(endpoint=f"{settings.OTLP_ENDPOINT}/v1/metrics")
                    if settings.OTLP_ENDPOINT
                    else ConsoleMetricExporter()
                )
                metric_reader = PeriodicExportingMetricReader(metric_exporter)
                meter_provider = MeterProvider(
                    resource=resource,
                    metric_readers=[metric_reader],
                )
                metrics.set_meter_provider(meter_provider)

                FastAPIInstrumentor.instrument_app(
                    app,
                    tracer_provider=tracer_provider,
                    meter_provider=meter_provider,
                    excluded_urls="/health,/metrics",
                )

                HTTPXClientInstrumentor().instrument()
                SQLAlchemyInstrumentor().instrument(
                    tracer_provider=tracer_provider,
                    enable_commenter=True,
                )
                RedisInstrumentor().instrument(tracer_provider=tracer_provider)

                logger.info("OpenTelemetry observability configured successfully")
            except Exception as error:  # pragma: no cover - defensive
                logger.error("Failed to setup OpenTelemetry", error=str(error))

        def get_tracer(name: str | None = None):
            """Return a tracer from the configured provider."""
            return trace.get_tracer(name or settings.APP_NAME)

        def get_meter(name: str | None = None):
            """Return a meter from the configured provider."""
            return metrics.get_meter(name or settings.APP_NAME)

else:
    setup_observability = NOOP_SETUP_OBSERVABILITY
    get_tracer = NOOP_GET_TRACER
    get_meter = NOOP_GET_METER


class ObservabilityMixin:
    """Mixin that provides access to tracer and meter helpers."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.tracer = get_tracer(self.__class__.__name__)
        self.meter = get_meter(self.__class__.__name__)

    def start_span(self, name: str, **attributes: object):
        """Start a span with optional attributes."""
        return self.tracer.start_span(name, **attributes)

    def create_counter(self, name: str, description: str, unit: str = ""):
        """Create a counter metric."""
        return self.meter.create_counter(name, description=description, unit=unit)

    def create_histogram(self, name: str, description: str, unit: str = ""):
        """Create a histogram metric."""
        return self.meter.create_histogram(name, description=description, unit=unit)

    def create_up_down_counter(self, name: str, description: str, unit: str = ""):
        """Create an up-down counter metric."""
        return self.meter.create_up_down_counter(
            name, description=description, unit=unit
        )


__all__ = [
    "NOOP_GET_METER",
    "NOOP_GET_TRACER",
    "NOOP_SETUP_OBSERVABILITY",
    "ObservabilityMixin",
    "get_meter",
    "get_tracer",
    "setup_observability",
]
