FROM mcr.microsoft.com/playwright:v1.64.1-noble@sha256:2f05f8a734509a7b3f26a912639488ee08f58a7b292d14d62271bcff9038768f
WORKDIR /fixture
COPY backend/tests/fixtures/browser_egress/package*.json ./
RUN npm ci --ignore-scripts --omit=dev
COPY backend/tests/fixtures/browser_egress/browser_fixture.cjs ./
USER pwuser
CMD ["node", "browser_fixture.cjs"]
