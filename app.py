import os

from flask import Flask, request

from opentelemetry import propagators, trace
from opentelemetry.exporter.otlp.trace_exporter import OTLPSpanExporter

from opentelemetry.instrumentation.wsgi import collect_request_attributes
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleExportSpanProcessor
from opentelemetry.trace.propagation.textmap import DictGetter

from opentelemetry.ext.honeycomb.sampling import DeterministicSampler

from grpc import ssl_channel_credentials

app = Flask(__name__)

sampler = DeterministicSampler(5)
trace.set_tracer_provider(TracerProvider(sampler=sampler))
tracer = trace.get_tracer_provider().get_tracer(__name__)

otlp_exporter = OTLPSpanExporter(
    endpoint="api.honeycomb.io:443",
    insecure=False,
    credentials=ssl_channel_credentials(),
    headers=(
        ("x-honeycomb-team", os.environ.get("HONEYCOMB_WRITE_KEY")),
        ("x-honeycomb-dataset", os.environ.get("HONEYCOMB_DATASET"))
    )
)

trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(ConsoleSpanExporter())
)
trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(otlp_exporter)
)

@app.route("/server_request")
def server_request():
    with tracer.start_as_current_span(
        "server_request",
        context=propagators.extract(DictGetter(), request.headers),
        kind=trace.SpanKind.SERVER,
        attributes=collect_request_attributes(request.environ)
    ):
        print(request.args.get("param"))
        return "served"

if __name__ == "__main__":
    app.run(port=8082)