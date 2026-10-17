FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.10.8 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

# Dependencies first, so code changes don't reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .

# Inside a container the proxy must listen on all interfaces. compose.yaml only
# publishes it on 127.0.0.1; set PROXY_AUTH_TOKEN before exposing it further.
EXPOSE 8082
CMD ["uv", "run", "--no-sync", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8082"]
