#!/bin/bash
set -e

# Get PORT from environment variable, default to 5000
PORT=${PORT:-5000}

# Start Gunicorn
exec python -m gunicorn app:app \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -


