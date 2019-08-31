ARG CONSUL_VERSION=1.5.3

FROM consul:${CONSUL_VERSION} AS consul

FROM python:3-alpine

ARG BUILD_ID=0
ARG CONSUL_VERSION
ARG VERSION=${CONSUL_VERSION}

LABEL build_id="${BUILD_ID}" \
      version="${VERSION}" \
      consul_version="${CONSUL_VERSION}" \
      description="KV Provisioned Consul Docker Image" \
      maintainer="Anton Trifonov <rin@pdffiller.team>"

COPY --from=consul /bin/consul /bin/consul
COPY --from=consul /usr/local/bin/docker-entrypoint.sh /usr/local/bin/consul-docker-entrypoint.sh
COPY --from=gosu/assets /opt/gosu /opt/gosu

ARG CONSUL_DATA_DIR=/consul/data
ARG CONSUL_CONFIG_DIR=/consul/config

RUN apk add --no-cache curl dumb-init libcap su-exec iputils jq && \
    pip install pyyaml python-consul --no-cache-dir && \
    ln -s /usr/bin/dumb-init /bin/dumb-init && \
    /opt/gosu/gosu.install.sh && \
    addgroup consul && \
    adduser -S -G consul consul && \
    mkdir -p \
        "${CONSUL_DATA_DIR}" \
        "${CONSUL_CONFIG_DIR}" && \
    chown -R consul:consul \
        "${CONSUL_DATA_DIR}" \
        "${CONSUL_CONFIG_DIR}" && \
    sed -i "s#^CONSUL_DATA_DIR=.*\$#CONSUL_DATA_DIR=${CONSUL_DATA_DIR}#" /usr/local/bin/consul-docker-entrypoint.sh && \
    sed -i "s#^CONSUL_CONFIG_DIR=.*\$#CONSUL_CONFIG_DIR=${CONSUL_CONFIG_DIR}#" /usr/local/bin/consul-docker-entrypoint.sh && \
    rm -rf /opt/gosu

COPY ./files /

RUN cd /usr/local/bin/ && \
    ln -s update-kv.py update-kv && \
    chmod +x docker-entrypoint.sh \
             gosu \
             update-kv.py \
             update-kv

EXPOSE 8500 8600 8600/udp

ENTRYPOINT ["docker-entrypoint.sh"]

CMD ["consul", "agent", "-server", "-bootstrap-expect=1", "-data-dir=/consul/data", "-client=0.0.0.0", "-ui"]
