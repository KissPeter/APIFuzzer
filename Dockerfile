FROM python:3.11.1-slim-bullseye as build
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update
RUN apt install -y --no-install-recommends gcc libc6-dev libssl-dev libcurl4-openssl-dev && rm -rf /var/lib/apt/lists/*
LABEL org.opencontainers.image.authors="peter.kiss@linuxadm.hu"
RUN pip install pycurl
RUN find / -type f -name libcurl.so.4

RUN find $HOME/.cache/pip -type f -name pycurl*.whl -exec cp {} /tmp \;
FROM python:3.11.1-slim-bullseye as pycurl
COPY --from=build  /tmp/*.whl  /tmp/
COPY --from=build  /usr/bin/curl-config  /usr/bin/curl-config
COPY --from=build  /usr/lib/x86_64-linux-gnu/  /usr/lib/x86_64-linux-gnu/
ENV PYCURL_CURL_CONFIG=/usr/bin/curl-config
ENV PYCURL_SSL_LIBRARY=nss
ENV PIP_NO_CACHE_DIR=yes
RUN pip install /tmp/*.whl && rm -rf /tmp/*.whl
CMD python -c "import pycurl"

FROM pycurl
WORKDIR /src/
COPY apifuzzer apifuzzer
COPY APIFuzzer .
COPY requirements.txt .
RUN pip install -r requirements.txt
ENTRYPOINT ./APIFuzzer $@
