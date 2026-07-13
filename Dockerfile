FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system gateway && adduser --system --ingroup gateway gateway

COPY pyproject.toml requirements.lock /app/
COPY gateway_server /app/gateway_server
COPY gateway_client /app/gateway_client
COPY noteweb/index.html noteweb/THIRD_PARTY_NOTICES.md /app/noteweb/
COPY noteweb/css /app/noteweb/css
COPY noteweb/js /app/noteweb/js
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-cache-dir --no-deps .

RUN mkdir -p /app/data && chown -R gateway:gateway /app

USER gateway
VOLUME /app/data
EXPOSE 18388

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:18388/healthz', timeout=3)"

CMD ["uvicorn", "gateway_server.main:app", "--host", "0.0.0.0", "--port", "18388", "--proxy-headers", "--forwarded-allow-ips=*"]
