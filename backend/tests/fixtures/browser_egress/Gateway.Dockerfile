FROM mcr.microsoft.com/playwright:v1.64.1-noble@sha256:2f05f8a734509a7b3f26a912639488ee08f58a7b292d14d62271bcff9038768f AS fixture_tls
RUN openssl req -x509 -newkey rsa:2048 -nodes -keyout /fixture-key.pem -out /fixture-cert.pem -days 1 -subj /CN=allowed.test >/dev/null 2>&1 && chmod 644 /fixture-key.pem
FROM python:3.12-slim
WORKDIR /fixture
COPY --from=fixture_tls /fixture-key.pem /fixture-cert.pem ./
COPY backend/app/core/browser_urls.py app/core/browser_urls.py
COPY backend/app/engine/browser_network.py app/engine/browser_network.py
COPY backend/app/engine/browser_gateway.py app/engine/browser_gateway.py
COPY backend/tests/fixtures/browser_egress/gateway_fixture.py gateway_fixture.py
COPY backend/tests/fixtures/browser_egress/fixture_server.py fixture_server.py
RUN mkdir /egress && chown 1001:1001 /egress
USER 1001:1001
VOLUME ["/egress"]
CMD ["python", "gateway_fixture.py"]
