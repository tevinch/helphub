FROM ghcr.io/alam00000/bentopdf-simple:v2.8.12@sha256:f96da8c4a347880b891d66aa2ebfa6b63f76277dafcfcdfa40c8e6b92c59ef44

COPY status-access-log.conf /etc/nginx/status-access-log.conf
RUN set -eu; \
    config=/etc/nginx/nginx.conf; \
    if [ "$(grep -c '^http {$' "$config")" -ne 1 ] || \
       grep -Eq '^[[:space:]]*access_log[[:space:]]' "$config"; then \
        echo "BentoPDF nginx layout changed. Check the access log configuration before building." >&2; \
        exit 1; \
    fi; \
    sed -i '/^http {$/a\    include /etc/nginx/status-access-log.conf;' "$config"; \
    nginx -t
