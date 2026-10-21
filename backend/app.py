import os
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="G.I KO KO AI API", version="1.0.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "https://gi-koko-ai.onrender.com").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])

class ChatRequest(BaseModel):
    provider: str = Field(pattern="^(gemini|modelgo)$")
    model: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=30000)
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=30)

@app.get("/api/health")
async def health():
    return {"ok": True, "service": "G.I KO KO AI API", "providers": {"gemini": bool(os.getenv("GEMINI_API_KEY")), "modelgo": bool(os.getenv("MODELG0_API_KEY") or os.getenv("MODELGO_API_KEY"))}}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    provider = req.provider
    async with httpx.AsyncClient(timeout=90) as client:
        if provider == "gemini":
            key = os.getenv("GEMINI_API_KEY", "").strip()
            if not key:
                raise HTTPException(503, "Gemini server key is not configured. Add GEMINI_API_KEY in Render Environment.")
            model = req.model.removeprefix("models/")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            contents = []
            for item in req.history[-20:]:
                role = "model" if item.get("role") == "ai" or item.get("role") == "model" else "user"
                text = str(item.get("text", ""))[:12000]
                if text:
                    contents.append({"role": role, "parts": [{"text": text}]})
            contents.append({"role": "user", "parts": [{"text": req.message}]})
            try:
                response = await client.post(url, params={"key": key}, json={"systemInstruction": {"parts": [{"text": "You are G.I KO KO AI. Reply in Burmese when the user writes Burmese; otherwise use the user's language."}]}, "contents": contents})
                data = response.json()
            except Exception as exc:
                raise HTTPException(502, f"Gemini request failed: {type(exc).__name__}")
            if response.is_error:
                raise HTTPException(response.status_code if response.status_code < 500 else 502, data.get("error", {}).get("message", "Gemini API request failed"))
            answer = "".join(p.get("text", "") for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", []))
            if not answer:
                raise HTTPException(502, "Gemini returned an empty response")
            return {"answer": answer, "provider": "gemini", "model": model}
        key = (os.getenv("MODELGO_API_KEY") or os.getenv("MODELG0_API_KEY") or "").strip()
        if not key:
            raise HTTPException(503, "ModelGo server key is not configured. Add MODELGO_API_KEY in Render Environment.")
        base = os.getenv("MODELGO_BASE_URL", "https://api.modelgo.ai/v1").rstrip("/")
        messages = [{"role": "system", "content": "You are G.I KO KO AI. Reply in Burmese when the user writes Burmese; otherwise use the user's language."}]
        for item in req.history[-20:]:
            role = "assistant" if item.get("role") == "ai" else "user"
            text = str(item.get("text", ""))[:12000]
            if text:
                messages.append({"role": role, "content": text})
        messages.append({"role": "user", "content": req.message})
        try:
            response = await client.post(base + "/chat/completions", headers={"Authorization": f"Bearer {key}"}, json={"model": req.model, "messages": messages, "stream": False})
            data = response.json()
        except Exception as exc:
            raise HTTPException(502, f"ModelGo request failed: {type(exc).__name__}")
        if response.is_error:
            raise HTTPException(response.status_code if response.status_code < 500 else 502, data.get("error", {}).get("message", "ModelGo API request failed"))
        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(answer, list):
            answer = "".join(str(x.get("text", "")) for x in answer if isinstance(x, dict))
        if not answer:
            raise HTTPException(502, "ModelGo returned an empty response")
        return {"answer": answer, "provider": "modelgo", "model": req.model}
