#!/bin/sh

set -eu

# Run migrations
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  # Run migrations
  alembic upgrade head
fi

exec "$@"
