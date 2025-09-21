"""
OpenTelemetry observability setup for distributed tracing and metrics.
"""

from opentelemetry import trace, metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def setup_observability(app):
    """Setup OpenTelemetry observability for the application"""

    try:
        # Create resource with service information
        resource = Resource.create({
            SERVICE_NAME: settings.APP_NAME,
            SERVICE_VERSION: "1.0.0",
            "environment": settings.ENVIRONMENT,
        })

        # Setup tracing
        tracer_provider = TracerProvider(resource=resource)

        # Configure span exporters
        if settings.OTLP_ENDPOINT:
            # Export to OTLP collector
            otlp_exporter = OTLPSpanExporter(endpoint=f"{settings.OTLP_ENDPOINT}/v1/traces")
            span_processor = BatchSpanProcessor(otlp_exporter)
        else:
            # Export to console for development
            console_exporter = ConsoleSpanExporter()
            span_processor = BatchSpanProcessor(console_exporter)

        tracer_provider.add_span_processor(span_processor)
        trace.set_tracer_provider(tracer_provider)

        # Setup metrics
        metric_reader = PeriodicExportingMetricReader(
            ConsoleMetricExporter() if not settings.OTLP_ENDPOINT
            else OTLPMetricExporter(endpoint=f"{settings.OTLP_ENDPOINT}/v1/metrics")
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=tracer_provider,
            meter_provider=meter_provider,
            excluded_urls="/health,/metrics",
        )

        # Instrument HTTP client
        HTTPXClientInstrumentor().instrument()

        # Instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument(
            tracer_provider=tracer_provider,
            enable_commenter=True,
        )

        # Instrument Redis
        RedisInstrumentor().instrument(tracer_provider=tracer_provider)

        logger.info("OpenTelemetry observability configured successfully")

    except Exception as e:
        logger.error("Failed to setup OpenTelemetry", error=str(e))
        # Don't raise exception - continue without observability


def get_tracer(name: str = None):
    """Get a tracer instance"""
    return trace.get_tracer(name or settings.APP_NAME)


def get_meter(name: str = None):
    """Get a meter instance"""
    return metrics.get_meter(name or settings.APP_NAME)


class ObservabilityMixin:
    """Mixin class to add observability to other classes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracer = get_tracer(self.__class__.__name__)
        self.meter = get_meter(self.__class__.__name__)

    def start_span(self, name: str, **attributes):
        """Start a new span"""
        return self.tracer.start_span(name, attributes=attributes)

    def create_counter(self, name: str, description: str, unit: str = ""):
        """Create a counter metric"""
        return self.meter.create_counter(name, description=description, unit=unit)

    def create_histogram(self, name: str, description: str, unit: str = ""):
        """Create a histogram metric"""
        return self.meter.create_histogram(name, description=description, unit=unit)

    def create_up_down_counter(self, name: str, description: str, unit: str = ""):
        """Create an up-down counter metric"""
        return self.meter.create_up_down_counter(name, description=description, unit=unit)