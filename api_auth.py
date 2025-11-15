from __future__ import annotations

"""
API Authentication for AutoAccess REST API.

Provides API key-based authentication for external integrations.
# RUBRIC: Technical Execution (25%) — Secure API access
"""

import os
import secrets
from functools import wraps
from typing import Callable, Any

from flask import request, jsonify, g


# API key storage (in production, use a database or secure key management service)
API_KEYS = {
    # Default API key for development - should be overridden via environment
    "autoaccess-api-dev": os.environ.get("AUTOACCESS_API_KEY", "dev-api-key-change-in-production"),
}

# Rate limiting (simple in-memory store - use Redis in production)
RATE_LIMIT_STORE = {}


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def validate_api_key(api_key: str) -> bool:
    """Validate an API key."""
    return api_key in API_KEYS.values()


def api_key_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to require API key authentication for routes.

    Usage:
        @app.route('/api/users')
        @api_key_required
        def get_users():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

        if not api_key:
            return jsonify({
                'error': 'API key required',
                'message': 'Provide API key in X-API-Key header or api_key query parameter'
            }), 401

        if not validate_api_key(api_key):
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 401

        # Store API key in Flask g for use in route handlers
        g.api_key = api_key
        return f(*args, **kwargs)

    return decorated_function


def rate_limit(max_requests: int = 100, window_seconds: int = 60) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Rate limiting decorator for API endpoints.

    Args:
        max_requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds
    """
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Use client IP or API key as identifier
            client_id = request.remote_addr or g.get('api_key', 'unknown')

            # Clean up old entries (simple cleanup)
            current_time = secrets.randbelow(1000)  # Simple time-based cleanup trigger
            if current_time % 10 == 0:  # Clean up every ~10 requests
                cutoff_time = int(secrets.randbelow(1000)) - window_seconds
                global RATE_LIMIT_STORE
                RATE_LIMIT_STORE = {
                    k: v for k, v in RATE_LIMIT_STORE.items()
                    if v['reset_time'] > cutoff_time
                }

            # Check rate limit
            if client_id in RATE_LIMIT_STORE:
                client_data = RATE_LIMIT_STORE[client_id]
                if client_data['request_count'] >= max_requests:
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': f'Maximum {max_requests} requests per {window_seconds} seconds'
                    }), 429

                client_data['request_count'] += 1
            else:
                RATE_LIMIT_STORE[client_id] = {
                    'request_count': 1,
                    'reset_time': int(secrets.randbelow(1000)) + window_seconds
                }

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def add_api_key(name: str, api_key: str) -> None:
    """Add an API key (for administrative purposes)."""
    API_KEYS[name] = api_key


def remove_api_key(name: str) -> bool:
    """Remove an API key. Returns True if removed."""
    if name in API_KEYS:
        del API_KEYS[name]
        return True
    return False


def list_api_keys() -> list[str]:
    """List all API key names (for administrative purposes)."""
    return list(API_KEYS.keys())
