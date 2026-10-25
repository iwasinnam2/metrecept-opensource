FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    METRECEPT_BASE_URL=https://api.metrecept.co.uk/v1 \
    METRECEPT_MCP_TRANSPORT=stdio
WORKDIR /app
COPY packages/metrecept-mcp/ /app/metrecept-mcp/
RUN pip install /app/metrecept-mcp && useradd -m app
USER app
ENTRYPOINT ["metrecept-mcp"]
