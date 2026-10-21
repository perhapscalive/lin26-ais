FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /bin/

# Application installation directory.
ARG APP_HOME="/opt/lin26-ais"

WORKDIR ${APP_HOME}
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Use the base image's Python and install a non-editable package from the lockfile.
ENV UV_PYTHON_DOWNLOADS=never
RUN uv sync --locked --no-cache --no-dev --no-editable --compile-bytecode

# Install as root, then run as an unprivileged user. Bind-mounted output paths
# can use the host's UID/GID via docker run --user instead.
RUN groupadd --gid 9876 lin26 \
    && useradd --uid 9876 --gid 9876 --create-home --no-log-init lin26
USER 9876:9876

ENV PATH="${APP_HOME}/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["lin26-ais"]
