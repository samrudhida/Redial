"""Application liveness route."""

from fastapi import APIRouter

from backend.app.config.settings import get_settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check")
async def health() -> dict[str, object]:
    settings = get_settings()
    razorpay_configured = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        # key_id is the public half of the Razorpay key pair — safe to expose
        # to the frontend, which needs it to initialise Checkout.js. The
        # secret never leaves the backend.
        "razorpay_configured": razorpay_configured,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID if razorpay_configured else None,
    }
