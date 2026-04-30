ARG OLLAMA_IMAGE=ollama/ollama:latest
FROM ${OLLAMA_IMAGE}

COPY models/ /opt/ollama/models/
COPY init-ollama.sh /usr/local/bin/init-ollama.sh

RUN chmod +x /usr/local/bin/init-ollama.sh

ENTRYPOINT ["/usr/local/bin/init-ollama.sh"]
