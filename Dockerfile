# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    mariadb-client && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* && \
    apt-get clean

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install pipenv
RUN python -m pip install --upgrade --no-cache-dir pip \
    && python -m pip install --no-cache-dir pipenv

WORKDIR /app

# Copy dependency files
COPY Pipfile Pipfile.lock ./

# Install project dependencies
RUN pipenv install --system --deploy --ignore-pipfile

# Stage 2: Final image
FROM python:3.12-slim AS runtime
ARG APP_VERSION
ARG APP_RELEASE_ID

# Install runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    mariadb-client \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create and switch to non-root 'bot' user
RUN useradd -m -d /app bot
WORKDIR /app
USER bot

# Copy application code
COPY --chown=bot:bot src src
COPY --chown=bot:bot alembic.ini alembic.ini

# Entrypoint script
COPY --chown=bot:bot docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

LABEL org.opencontainers.image.version=$APP_VERSION \
    org.opencontainers.image.revision=$APP_RELEASE_ID

# Set default command
CMD ["python", "-m", "src.bot"]
