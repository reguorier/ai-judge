FROM python:3.11-slim

LABEL org.opencontainers.image.title="AI Judge"
LABEL org.opencontainers.image.description="Local-first AI jury skill with evidence tracing, dissent, and reasoning trees"
LABEL org.opencontainers.image.version="3.2.0"
LABEL org.opencontainers.image.source="https://github.com/reguorider-gif/ai-judge"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates jq nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/ai-judge
COPY pyproject.toml .
COPY README.md LICENSE ./
COPY cli/ cli/
COPY core/ core/

RUN pip install --no-cache-dir -e .

ENV AI_JUDGE_ROOT=/data
ENV PYTHONUNBUFFERED=1
VOLUME ["/data"]

ENTRYPOINT ["ai-judge"]
CMD ["--help"]
