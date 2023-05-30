FROM python:3.11-slim-bullseye as builder
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1
RUN apt update && apt upgrade -y  && apt install -y --no-install-recommends gcc libc6-dev libssl-dev libcurl4-openssl-dev && rm -rf /var/lib/apt/lists/*
LABEL org.opencontainers.image.authors="peter.kiss@linuxadm.hu"
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip wheel --no-deps --wheel-dir /app/wheels  -r requirements.txt

FROM python:3.11-slim-bullseye  as pycurl
COPY --from=builder  /usr/bin/curl-config  /usr/bin/curl-config
COPY --from=builder  /usr/lib/x86_64-linux-gnu/  /usr/lib/x86_64-linux-gnu/
ENV PYCURL_CURL_CONFIG=/usr/bin/curl-config
ENV PYCURL_SSL_LIBRARY=nss
ENV PIP_NO_CACHE_DIR=1
COPY --from=builder /app/wheels /wheels/
RUN pip install --upgrade pip
RUN pip install /wheels/*
CMD python -c "import pycurl"

FROM pycurl as final
ENV PIP_NO_CACHE_DIR=1
WORKDIR /src/
COPY --from=builder /app/wheels /wheels/
RUN pip install /wheels/*
COPY apifuzzer apifuzzer
COPY APIFuzzer .
COPY entrypoint.sh .
ENTRYPOINT ["./entrypoint.sh"]
HEALTHCHECK --interval=5s --timeout=5s --retries=3 --start-period=2s CMD pgrep APIFuzzer
