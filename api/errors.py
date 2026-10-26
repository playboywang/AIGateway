"""Shared API errors."""

from fastapi import HTTPException


def gateway_unavailable(protocol: str) -> HTTPException:
    """Build the response used while the gateway backend is not configured."""
    return HTTPException(
        status_code=503,
        detail={
            "code": "gateway_backend_unavailable",
            "message": "The gateway backend is not configured yet.",
            "protocol": protocol,
        },
    )
