FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    OHM_BASE_URL=https://api.metrecept.co.uk/v1 \
    OHM_MCP_TRANSPORT=stdio
WORKDIR /app
COPY packages/ohm-mcp/ /app/ohm-mcp/
RUN pip install /app/ohm-mcp && useradd -m app
USER app
ENTRYPOINT ["ohm-mcp"]
