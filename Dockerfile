FROM python:3.11-slim

LABEL org.opencontainers.image.title="SynthAudit" \
      org.opencontainers.image.description="Reference-free auditing of synthetic datasets for generator artifacts before machine learning" \
      org.opencontainers.image.source="https://github.com/rvndye/synthaudit" \
      org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir ".[causal,notebook]"

COPY datasets ./datasets
COPY tests ./tests

# default: planted-artifact self-validation
CMD ["python", "-m", "synthaudit", "selftest"]
