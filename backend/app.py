import os, json, re
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="G.I KO KO AI API", version="2.0.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "https://gi-koko-ai.onrender.com").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST","OPTIONS"], allow_headers=["Content-Type","Authorization","X-Admin-Secret"])

class ChatRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=30000)
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=30)

class ProviderConfig(BaseModel):
    id: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=8, max_length=500)
    api_key: str = Field(min_length=1, max_length=500)
    models: list[str] = Field(min_length=1, max_length=100)
    auth_header: str = Field(default="Authorization", max_length=100)
    auth_scheme: str = Field(default="Bearer", max_length=40)
    extra_headers: dict[str, str] = Field(default_factory=dict)
    chat_path: str = Field(default="/chat/completions", max_length=200)

def _custom():
    try: return json.loads(os.getenv("CUSTOM_PROVIDERS_JSON", "{}"))
    except Exception: return {}

@app.get("/api/health")
async def health():
    customs = _custom()
    return {"ok": True, "service": "G.I KO KO AI API", "providers": {
        "gemini": bool(os.getenv("GEMINI_API_KEY")), "modelgo": bool(os.getenv("MODELGO_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")), "groq": bool(os.getenv("GROQ_API_KEY")),
        "openrouter": bool(os.getenv("OPENROUTER_API_KEY")), "custom": len(customs)
    }}

@app.get("/api/providers")
async def providers():
    result = []
    if os.getenv("GEMINI_API_KEY"): result.append({"id":"gemini","name":"Google Gemini","models":["gemini-2.5-flash","gemini-2.5-pro"]})
    builtins = [
      ("openai","OpenAI","OPENAI_API_KEY","https://api.openai.com/v1",["gpt-4.1-mini","gpt-4.1"]),
      ("groq","Groq","GROQ_API_KEY","https://api.groq.com/openai/v1",["openai/gpt-oss-120b","llama-3.3-70b-versatile"]),
      ("openrouter","OpenRouter","OPENROUTER_API_KEY","https://openrouter.ai/api/v1",["openai/gpt-oss-120b"]),
      ("deepseek","DeepSeek","DEEPSEEK_API_KEY","https://api.deepseek.com/v1",["deepseek-chat","deepseek-reasoner"]),
      ("mistral","Mistral AI","MISTRAL_API_KEY","https://api.mistral.ai/v1",["mistral-small-latest","mistral-large-latest"]),
      ("together","Together AI","TOGETHER_API_KEY","https://api.together.xyz/v1",["meta-llama/Llama-3.3-70B-Instruct-Turbo"]),
      ("cerebras","Cerebras","CEREBRAS_API_KEY","https://api.cerebras.ai/v1",["llama-3.3-70b"]),
      ("xai","xAI","XAI_API_KEY","https://api.x.ai/v1",["grok-3-mini"])
    ]
    for pid,name,key,base,models in builtins:
        if os.getenv(key): result.append({"id":pid,"name":name,"models":models})
    for pid,p in _custom().items():
        result.append({"id":"custom:"+pid,"name":p.get("name",pid),"models":p.get("models",[])})
    return {"providers":result}

@app.post("/api/admin/providers")
async def save_custom_provider(cfg: ProviderConfig, x_admin_secret: str = Header(default="")):
    expected = os.getenv("ADMIN_SECRET", "")
    render_token = os.getenv("RENDER_API_KEY", "")
    service_id = os.getenv("RENDER_SERVICE_ID", "")
    if not expected or not render_token or not service_id:
        raise HTTPException(503, "Admin setup incomplete. Configure ADMIN_SECRET, RENDER_API_KEY and RENDER_SERVICE_ID in Render Environment.")
    if not x_admin_secret or not __import__("hmac").compare_digest(x_admin_secret, expected):
        raise HTTPException(401, "Admin authentication failed.")
    pid = re.sub(r"[^a-z0-9_-]", "-", cfg.id.lower()).strip("-")[:60]
    if not pid: raise HTTPException(400, "Invalid provider ID.")
    if not cfg.base_url.startswith("https://"):
        raise HTTPException(400, "Provider endpoint must use HTTPS.")
    configs = _custom()
    configs[pid] = {"name":cfg.name, "base_url":cfg.base_url.rstrip("/"), "api_key":cfg.api_key,
        "models":cfg.models, "auth_header":cfg.auth_header, "auth_scheme":cfg.auth_scheme,
        "extra_headers":cfg.extra_headers, "chat_path":cfg.chat_path if cfg.chat_path.startswith("/") else "/"+cfg.chat_path}
    env_value = json.dumps(configs, separators=(",",":"), ensure_ascii=False)
    if len(env_value) > 9000: raise HTTPException(413, "Provider config is too large for one environment variable.")
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.put(f"https://api.render.com/v1/services/{service_id}/env-vars",
                headers={"Authorization":f"Bearer {render_token}","Content-Type":"application/json"},
                json=[{"key":"CUSTOM_PROVIDERS_JSON","value":env_value}])
        except Exception as exc:
            raise HTTPException(502, f"Render environment update failed: {type(exc).__name__}")
    if response.is_error:
        raise HTTPException(502, f"Render API rejected environment update (HTTP {response.status_code}). Check RENDER_API_KEY permissions and service ID.")
    return {"ok":True,"id":"custom:"+pid,"name":cfg.name,"models":cfg.models,"message":"Saved to Render Environment. Service may restart before changes take effect."}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    provider = req.provider
    history = req.history[-20:]
    system = "You are G.I KO KO AI. Reply in Burmese when the user writes Burmese; otherwise use the user's language."
    if provider == "gemini":
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key: raise HTTPException(503, "GEMINI_API_KEY is not configured.")
        model = req.model.removeprefix("models/")
        contents=[]
        for item in history:
            role = "model" if item.get("role") in ("ai","assistant","model") else "user"
            txt=str(item.get("text",item.get("content","")))[:12000]
            if txt: contents.append({"role":role,"parts":[{"text":txt}]})
        contents.append({"role":"user","parts":[{"text":req.message}]})
        async with httpx.AsyncClient(timeout=90) as client:
            response=await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",headers={"x-goog-api-key":key},json={"systemInstruction":{"parts":[{"text":system}]},"contents":contents})
        data=response.json()
        if response.is_error: raise HTTPException(502, data.get("error",{}).get("message","Gemini API request failed"))
        answer="".join(x.get("text","") for x in data.get("candidates",[{}])[0].get("content",{}).get("parts",[]))
        if not answer: raise HTTPException(502,"Gemini returned an empty response.")
        return {"answer":answer,"provider":provider,"model":model}
    builtins={
      "openai":("OPENAI_API_KEY","https://api.openai.com/v1"),
      "groq":("GROQ_API_KEY","https://api.groq.com/openai/v1"),
      "openrouter":("OPENROUTER_API_KEY","https://openrouter.ai/api/v1"),
      "deepseek":("DEEPSEEK_API_KEY","https://api.deepseek.com/v1"),
      "mistral":("MISTRAL_API_KEY","https://api.mistral.ai/v1"),
      "anthropic":("ANTHROPIC_API_KEY","https://api.anthropic.com/v1"),
      "together":("TOGETHER_API_KEY","https://api.together.xyz/v1"),
      "fireworks":("FIREWORKS_API_KEY","https://api.fireworks.ai/inference/v1"),
      "cerebras":("CEREBRAS_API_KEY","https://api.cerebras.ai/v1"),
      "sambanova":("SAMBANOVA_API_KEY","https://api.sambanova.ai/v1"),
      "xai":("XAI_API_KEY","https://api.x.ai/v1"),
      "modelgo":("MODELGO_API_KEY",os.getenv("MODELGO_BASE_URL","https://api.modelgo.ai/v1").rstrip("/"))
    }
    config=None
    if provider.startswith("custom:"):
        config=_custom().get(provider.split(":",1)[1])
        if not config: raise HTTPException(503,"Custom provider is not configured in backend environment.")
        key=config["api_key"]; base=config["base_url"]; path=config.get("chat_path","/chat/completions")
        auth_header=config.get("auth_header","Authorization"); scheme=config.get("auth_scheme","Bearer")
        headers={auth_header:(scheme+" "+key).strip()}
        headers.update(config.get("extra_headers",{}))
    else:
        if provider not in builtins: raise HTTPException(400,"Unsupported provider.")
        env_name,base=builtins[provider]; key=os.getenv(env_name,"").strip()
        if not key: raise HTTPException(503,f"{env_name} is not configured in backend Environment.")
        path="/messages" if provider=="anthropic" else "/chat/completions"
        headers={"Authorization":f"Bearer {key}"}
        if provider=="anthropic": headers={"x-api-key":key,"anthropic-version":"2023-06-01"}
    if provider=="anthropic":
        payload={"model":req.model,"max_tokens":2048,"system":system,"messages":[{"role":"user" if x.get("role")!="ai" else "assistant","content":str(x.get("text",""))[:12000]} for x in history]+[{"role":"user","content":req.message}]}
    else:
        msgs=[{"role":"system","content":system}]
        for x in history:
            role="assistant" if x.get("role") in ("ai","assistant","model") else "user"
            txt=str(x.get("text",x.get("content","")))[:12000]
            if txt: msgs.append({"role":role,"content":txt})
        msgs.append({"role":"user","content":req.message})
        payload={"model":req.model,"messages":msgs,"stream":False}
    async with httpx.AsyncClient(timeout=90) as client:
        try: response=await client.post(base+path,headers=headers,json=payload)
        except Exception as exc: raise HTTPException(502,f"Provider request failed: {type(exc).__name__}")
    try: data=response.json()
    except Exception: data={}
    if response.is_error: raise HTTPException(502,data.get("error",{}).get("message",f"Provider HTTP {response.status_code}"))
    if provider=="anthropic": answer="".join(x.get("text","") for x in data.get("content",[]) if x.get("type")=="text")
    else:
        answer=data.get("choices",[{}])[0].get("message",{}).get("content","")
        if isinstance(answer,list): answer="".join(str(x.get("text","")) for x in answer if isinstance(x,dict))
    if not answer: raise HTTPException(502,"Provider returned an empty response.")
    return {"answer":answer,"provider":provider,"model":req.model}
