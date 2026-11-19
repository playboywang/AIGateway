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

def gateway_capability_unavailable(protocol: str, capability: str) -> HTTPException:
    """Return 501 when the selected provider protocol lacks a capability."""
    return HTTPException(
        status_code=501,
        detail={
            "code": "gateway_capability_unavailable",
            "message": f"{capability} is not available for {protocol}",
            "protocol": protocol,
            "capability": capability,
        },
    )
