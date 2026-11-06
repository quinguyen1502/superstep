FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
WORKDIR /opt/browser-gateway
COPY backend/app/core/browser_urls.py app/core/browser_urls.py
COPY backend/app/engine/browser_network.py app/engine/browser_network.py
COPY backend/app/engine/browser_gateway.py app/engine/browser_gateway.py
RUN mkdir /egress && chown 1001:1001 /egress
USER 1001:1001
VOLUME ["/egress"]
CMD ["python", "-m", "app.engine.browser_gateway"]
