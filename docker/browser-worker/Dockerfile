FROM node:24-bookworm-slim@sha256:c86ecead9e55a5210ac1727de38a4ca840bf03dcaf34dc9749addbf383b1920c
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
WORKDIR /opt/browser-worker
COPY package*.json ./
RUN npm ci --ignore-scripts --omit=dev && npx playwright-core install --with-deps chromium && rm -rf /var/lib/apt/lists/* /root/.npm
COPY contracts.json worker.cjs rpc.cjs ./
RUN groupadd --gid 1001 browser && useradd --uid 1001 --gid 1001 --no-create-home browser
USER 1001:1001
CMD ["node", "worker.cjs"]
