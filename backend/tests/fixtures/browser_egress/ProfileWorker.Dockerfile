# TEST ONLY: production worker code plus one disposable CA; TLS verification stays enabled.
FROM superstep-browser-egress-gateway:task-0242 AS fixture
FROM superstep-browser-worker:1
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libnss3-tools && rm -rf /var/lib/apt/lists/*
COPY --from=fixture /fixture/fixture-cert.pem /opt/fixture-ca.pem
RUN mkdir /opt/fixture-nssdb && certutil -N --empty-password -d sql:/opt/fixture-nssdb && certutil -A -d sql:/opt/fixture-nssdb -n disposable-fixture -t 'C,,' -i /opt/fixture-ca.pem && chmod -R a+rX /opt/fixture-nssdb
USER 1001:1001
CMD ["sh", "-c", "mkdir -p /tmp/.pki/nssdb && cp /opt/fixture-nssdb/* /tmp/.pki/nssdb/ && exec node worker.cjs"]
