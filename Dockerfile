ARG PYTHON_IMAGE=python:3.13-slim-bookworm
FROM ${PYTHON_IMAGE} AS builder
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libssl-dev \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*
LABEL org.opencontainers.image.authors="peter.kiss@linuxadm.hu"
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip wheel --wheel-dir /app/wheels -r requirements.txt

FROM ${PYTHON_IMAGE} AS final
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcurl4 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src/
COPY --from=builder /app/wheels /wheels/
RUN pip install --upgrade pip && pip install /wheels/*
COPY apifuzzer apifuzzer
COPY setup.py .
COPY README.md .
COPY requirements.txt .
RUN pip install -e .
COPY entrypoint.sh .
ENTRYPOINT ["./entrypoint.sh"]
HEALTHCHECK --interval=5s --timeout=5s --retries=3 --start-period=2s CMD pgrep -f "apifuzzer"
