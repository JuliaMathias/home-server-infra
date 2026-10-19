FROM nvidia/cuda:13.4.3-cudnn-runtime-ubuntu24.04@sha256:534ea2e94fd17f053b4422d094f50a43a7e75a03240c4b89cbe9ad42085ec1c3 AS runtime
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PATH=/opt/venv/bin:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv
WORKDIR /app
COPY requirements.lock ./
RUN pip install -r requirements.lock
COPY service.py ./
USER 1000:1000
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]

FROM runtime AS test
USER root
COPY requirements-test.in ./
RUN apt-get update && apt-get install -y --no-install-recommends espeak-ng \
    && rm -rf /var/lib/apt/lists/* \
    && pip install -r requirements-test.in
COPY tests ./tests
ENV PYTHONPATH=/app
USER 1000:1000
CMD ["pytest", "-q", "-p", "no:cacheprovider", "tests"]
