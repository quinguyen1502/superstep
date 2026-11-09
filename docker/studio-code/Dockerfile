# Image for Tool nodes in Code mode: the standard library plus a few pinned packages.
# The server passes the runner on the command line (python -I -c ...), so nothing of the studio is copied in.
# Build: docker build -t studio-code:1 docker/studio-code   (STUDIO_CODE_IMAGE picks another tag)
FROM python:3.12-slim
RUN pip install --no-cache-dir --disable-pip-version-check pydantic==2.14.1 python-dateutil==2.9.0.post0 \
    && rm -rf /root/.cache
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /tmp
CMD ["python", "-c", "print('studio-code: run by the studio, not directly')"]
