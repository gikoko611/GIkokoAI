"""G.I KO KO Automation API foundation.

This module intentionally reports connector readiness only. Publishing is disabled
until each platform's official OAuth/API permissions and persistent job storage
are configured. Never expose token values through API responses or logs.
"""
import os
from fastapi import APIRouter, Header, HTTPException
import hmac

router = APIRouter(prefix="/api/automation", tags=["automation"])

PLATFORMS = {
    "facebook_page": {
        "label": "Facebook Page",
        "required": ["META_PAGE_ACCESS_TOKEN", "META_PAGE_ID"],
        "docs": "https://developers.facebook.com/docs/pages-api/"
    },
    "instagram": {
        "label": "Instagram",
        "required": ["META_IG_ACCESS_TOKEN", "META_IG_USER_ID"],
        "docs": "https://developers.facebook.com/docs/instagram-platform/"
    },
    "youtube": {
        "label": "YouTube",
        "required": ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"],
        "docs": "https://developers.google.com/youtube/v3"
    },
    "tiktok": {
        "label": "TikTok",
        "required": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_ACCESS_TOKEN"],
        "docs": "https://developers.tiktok.com/doc/content-posting-api-get-started"
    },
}

def _admin_ok(value: str) -> bool:
    expected = os.getenv("AUTOMATION_ADMIN_SECRET", "")
    return bool(expected and value and hmac.compare_digest(value, expected))

@router.get("/status")
async def automation_status():
    """Return connector readiness without returning any credential material."""
    items = {}
    for key, spec in PLATFORMS.items():
        missing = [name for name in spec["required"] if not os.getenv(name, "").strip()]
        items[key] = {
            "name": spec["label"],
            "configured": not missing,
            "missing_credentials": missing,
            "state": "credentials_ready_needs_api_validation" if not missing else "not_connected",
            "documentation": spec["docs"],
            "publishing_enabled": False
        }
    return {
        "service": "G.I KO KO Automation",
        "mode": "auto",
        "status": "foundation",
        "publishing_enabled": False,
        "reason": "Official OAuth/API validation and persistent scheduled-job storage are not configured yet.",
        "platforms": items
    }

@router.post("/admin/check")
async def automation_admin_check(x_automation_secret: str = Header(default="")):
    """Verify admin-secret configuration without returning the secret."""
    if not _admin_ok(x_automation_secret):
        raise HTTPException(status_code=401, detail="Automation admin authentication failed.")
    return {"ok": True, "message": "Automation admin authentication successful."}
