# Image for TypeScript Tool nodes in Code mode: Deno plus a few pre-cached npm packages.
# The server passes the runner on the command line (a data: URL), so nothing of the studio is copied in.
# At run time the container has no network (--network none), a read-only root and an arbitrary non-root uid, and
# Deno runs with no permission flag plus --cached-only: only the packages cached here can be imported.
# Build: docker build -t studio-code-ts:1 docker/studio-code-ts   (STUDIO_CODE_TS_IMAGE picks another tag;
# keep STUDIO_CODE_TS_PACKAGES in line with deps.ts when you change it)
FROM denoland/deno:debian-2.9.8
ENV DENO_DIR=/opt/deno-cache NO_COLOR=1 DENO_NO_UPDATE_CHECK=1
WORKDIR /opt/studio-deps
COPY deps.ts .
RUN deno cache --no-config --no-lock deps.ts \
    && chmod -R a+rX /opt/deno-cache \
    && rm -f deps.ts
WORKDIR /tmp
# the image's deno user; the studio runs it with its own --user anyway
USER 1993:1993
CMD ["deno", "eval", "console.log('studio-code-ts: run by the studio, not directly')"]
