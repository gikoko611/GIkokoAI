"""G.I KO KO Automation API foundation.

This module intentionally reports connector readiness only. Publishing is disabled
until each platform's official OAuth/API permissions and persistent job storage
are configured. Never expose token values through API responses or logs.
"""
import os
from fastapi import APIRouter, Header, HTTPException
import hmac
import httpx
from pydantic import BaseModel, Field

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

class SocialAIRequest(BaseModel):
    platform: str = Field(min_length=1, max_length=40)
    goal: str = Field(min_length=1, max_length=300)
    topic: str = Field(min_length=1, max_length=4000)
    tone: str = Field(default="friendly", max_length=80)
    language: str = Field(default="Burmese", max_length=40)

@router.get("/ai/status")
async def social_ai_status():
    return {
        "openai_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        "mode": "draft_only",
        "publishing_enabled": False
    }

@router.post("/ai/plan")
async def social_ai_plan(req: SocialAIRequest):
    """Use OpenAI as the social-content copilot. Drafts only; never publishes."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "OPENAI_API_KEY is not configured in Render Environment.")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
    if req.platform not in {"facebook_page", "instagram", "youtube", "tiktok"}:
        raise HTTPException(400, "Unsupported social platform.")
    system = (
        "You are G.I KO KO AI Social Media Manager. Create useful, platform-appropriate "
        "content drafts. Return Burmese by default when language is Burmese. Include "
        "a concise hook, caption/script, relevant hashtags, and a suggested call to action. "
        "For YouTube include a title and description. Never claim you published or scheduled "
        "anything. Do not invent analytics or account facts. Clearly label suggestions."
    )
    user = (
        f"Platform: {req.platform}\nGoal: {req.goal}\nTone: {req.tone}\n"
        f"Output language: {req.language}\nTopic / brief: {req.topic}"
    )
    async with httpx.AsyncClient(timeout=90) as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages":[
                    {"role":"system","content":system},
                    {"role":"user","content":user}
                ], "temperature":0.7}
            )
        except Exception as exc:
            raise HTTPException(502, f"OpenAI request failed: {type(exc).__name__}")
    try:
        data = response.json()
    except Exception:
        data = {}
    if response.is_error:
        detail = data.get("error", {}).get("message", f"OpenAI HTTP {response.status_code}")
        raise HTTPException(502, detail[:500])
    draft = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not draft:
        raise HTTPException(502, "OpenAI returned an empty draft.")
    return {"ok": True, "provider":"openai", "model":model, "platform":req.platform,
            "draft":draft, "published":False, "mode":"draft_only"}
