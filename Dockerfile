FROM python:3.11-slim

LABEL org.opencontainers.image.title="AI Judge"
LABEL org.opencontainers.image.description="Multi-model AI jury system"
LABEL org.opencontainers.image.version="2.0.0"
LABEL org.opencontainers.image.source="https://github.com/reguorier/ai-judge"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates jq nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/ai-judge
COPY pyproject.toml .
COPY cli/ cli/
COPY core/ core/

RUN pip install --no-cache-dir -e .

ENV AI_JUDGE_ROOT=/data
ENV PYTHONUNBUFFERED=1
VOLUME ["/data"]

ENTRYPOINT ["ai-judge"]
CMD ["--help"]
