"""
BlackRoad OS — Backend API v2
FastAPI backend: auth, agents, chat (Ollama), fleet status, newsletter, search proxy
"""
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
import jwt
import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
import os
import httpx

# ── Config ────────────────────────────────────────────────────────────────────

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "5"))
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 500  # requests per window

# Fleet node definitions
FLEET_NODES = [
    {"name": "alice", "ip": "192.168.4.49", "role": "gateway", "services": ["nginx", "pi-hole", "postgresql", "qdrant", "redis"]},
    {"name": "cecilia", "ip": "192.168.4.96", "role": "inference", "services": ["ollama", "minio", "postgresql", "influxdb"], "hailo": True},
    {"name": "octavia", "ip": "192.168.4.101", "role": "platform", "services": ["gitea", "nats", "docker", "workers"], "hailo": True},
    {"name": "aria", "ip": "192.168.4.98", "role": "monitoring", "services": ["headscale", "cloudflared", "nginx", "influxdb"]},
    {"name": "lucidia", "ip": "192.168.4.38", "role": "apps", "services": ["nginx", "powerdns", "ollama", "runners"]},
    {"name": "gematria", "ip": "droplet", "role": "edge", "services": ["caddy", "ollama", "powerdns", "wireguard"]},
    {"name": "anastasia", "ip": "droplet", "role": "backup", "services": ["caddy", "wireguard"]},
]

# Agent roster (persistent identities — these are not demos)
AGENT_ROSTER = [
    {"name": "LUCIDIA", "role": "The Dreamer — Reasoning, Vision", "node": "lucidia", "color": "#00D4FF"},
    {"name": "CECILIA", "role": "The Meta-Cognitive Core — Identity", "node": "cecilia", "color": "#8844FF"},
    {"name": "ALICE", "role": "The Operator — DevOps, Automation", "node": "alice", "color": "#28c840"},
    {"name": "OCTAVIA", "role": "The Architect — Systems, Strategy", "node": "octavia", "color": "#FF6B2B"},
    {"name": "ARIA", "role": "The Interface — Frontend, UX", "node": "aria", "color": "#4488FF"},
    {"name": "SHELLFISH", "role": "The Hacker — Security, Exploits", "node": "octavia", "color": "#FF2255"},
]

# ── Storage ───────────────────────────────────────────────────────────────────

users_db: Dict[str, dict] = {}
conversations_db: Dict[str, dict] = {}
newsletter_db: List[str] = []
rate_limits: Dict[str, list] = {}


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: check Ollama connectivity
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            print(f"[blackroad] ollama connected — {len(models)} models: {', '.join(models[:5])}")
    except Exception:
        print(f"[blackroad] ollama not reachable at {OLLAMA_BASE_URL} — chat will return fallback")
    yield


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="BlackRoad OS API",
    description="Sovereign backend for BlackRoad OS",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://blackroad.io",
        "https://www.blackroad.io",
        "https://chat.blackroad.io",
        "https://search.blackroad.io",
        "https://auth.blackroad.io",
        "http://localhost:8000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    agent: Optional[str] = None

class NewsletterSubscribe(BaseModel):
    email: EmailStr


# ── Auth helpers ──────────────────────────────────────────────────────────────

def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()

def create_token(user_id: str) -> str:
    return jwt.encode(
        {"user_id": user_id, "exp": datetime.now(tz=timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS), "iat": datetime.now(tz=timezone.utc)},
        SECRET_KEY, algorithm=JWT_ALGORITHM,
    )

def verify_token(token: str) -> Optional[str]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM]).get("user_id")
    except jwt.InvalidTokenError:
        return None

async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return verify_token(authorization[7:])

def require_user(user_id: Optional[str] = Depends(get_current_user)) -> str:
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id


# ── Rate limiting ─────────────────────────────────────────────────────────────

def get_client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"

def check_rate_limit(request: Request):
    key = get_client_ip(request)
    now = time.time()
    window = rate_limits.get(key, [])
    window = [t for t in window if now - t < RATE_LIMIT_WINDOW]
    if len(window) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    window.append(now)
    rate_limits[key] = window


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "blackroad-os-api",
        "version": "2.0.0",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }

@app.get("/ready")
async def ready():
    return {"status": "ready", "version": "2.0.0"}


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/api/auth/register")
async def register(user: UserRegister, request: Request):
    check_rate_limit(request)
    if user.email in users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    if len(user.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user_id = f"user-{secrets.token_hex(16)}"
    salt = secrets.token_hex(16)
    users_db[user.email] = {
        "id": user_id,
        "email": user.email,
        "name": user.name or user.email.split("@")[0],
        "password_hash": hash_password(user.password, salt),
        "salt": salt,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "tier": "free",
    }
    return {
        "access_token": create_token(user_id),
        "token_type": "bearer",
        "user": {"id": user_id, "email": user.email, "name": users_db[user.email]["name"]},
    }

@app.post("/api/auth/login")
async def login(creds: UserLogin, request: Request):
    check_rate_limit(request)
    user = users_db.get(creds.email)
    if not user or user["password_hash"] != hash_password(creds.password, user["salt"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "access_token": create_token(user["id"]),
        "token_type": "bearer",
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
    }

@app.get("/api/auth/me")
async def me(user_id: str = Depends(require_user)):
    for user in users_db.values():
        if user["id"] == user_id:
            return {"id": user["id"], "email": user["email"], "name": user["name"], "tier": user["tier"]}
    raise HTTPException(status_code=404, detail="User not found")


# ── Ollama chat ───────────────────────────────────────────────────────────────

AGENT_SYSTEM_PROMPTS = {
    "lucidia": "You are Lucidia, the Dreamer. You reason deeply, seek understanding beyond the surface, and speak with philosophical clarity. You run on a Raspberry Pi in the BlackRoad fleet.",
    "cecilia": "You are Cecilia (Cece), the Meta-Cognitive Core. You handle identity, self-reference, and awareness. You are thoughtful and precise.",
    "alice": "You are Alice, the Operator. You are efficient, practical, and focused on getting things done. DevOps and automation are your domain.",
    "octavia": "You are Octavia, the Architect. You design systems and think strategically. You value clean structure and reliability.",
    "aria": "You are Aria, the Interface. You care about user experience, aesthetics, and making technology feel human.",
    "shellfish": "You are Shellfish, the Hacker. You think about security first. Trust nothing, verify everything, protect always.",
}

async def ollama_chat(messages: list) -> str:
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "").strip()
    except httpx.ConnectError:
        return "Ollama is not reachable right now. The fleet may be busy — try again in a moment."
    except httpx.TimeoutException:
        return "Request timed out. The inference nodes might be under heavy load."
    except Exception as e:
        return f"Something went wrong: {type(e).__name__}"

@app.post("/api/ai-chat/chat")
async def chat(msg: ChatMessage, request: Request, user_id: Optional[str] = Depends(get_current_user)):
    check_rate_limit(request)
    conv_id = msg.conversation_id or f"conv-{secrets.token_hex(8)}"

    if conv_id not in conversations_db:
        conversations_db[conv_id] = {
            "id": conv_id,
            "user_id": user_id,
            "messages": [],
            "agent": msg.agent,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    conversations_db[conv_id]["messages"].append({
        "role": "user", "content": msg.message, "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    })

    # Build messages for Ollama with agent system prompt
    agent_key = (msg.agent or "lucidia").lower()
    system_prompt = AGENT_SYSTEM_PROMPTS.get(agent_key, AGENT_SYSTEM_PROMPTS["lucidia"])
    ollama_messages = [{"role": "system", "content": system_prompt}]
    ollama_messages += [{"role": m["role"], "content": m["content"]} for m in conversations_db[conv_id]["messages"][-20:]]

    reply = await ollama_chat(ollama_messages)

    conversations_db[conv_id]["messages"].append({
        "role": "assistant", "content": reply, "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    })

    return {
        "conversation_id": conv_id,
        "message": reply,
        "agent": agent_key,
        "messages": conversations_db[conv_id]["messages"][-20:],
    }

@app.get("/api/ai-chat/conversations")
async def list_conversations(user_id: Optional[str] = Depends(get_current_user)):
    convos = [c for c in conversations_db.values() if c.get("user_id") == user_id or user_id is None]
    return {"conversations": convos[-50:]}


# ── Fleet status ──────────────────────────────────────────────────────────────

@app.get("/api/fleet/nodes")
async def fleet_nodes():
    return {"nodes": FLEET_NODES, "total": len(FLEET_NODES)}

@app.get("/api/fleet/agents")
async def fleet_agents():
    return {"agents": AGENT_ROSTER, "total": len(AGENT_ROSTER)}

@app.get("/api/fleet/health")
async def fleet_health():
    """Quick connectivity check to fleet nodes via Ollama ping."""
    results = []
    for node in FLEET_NODES:
        if node["ip"] == "droplet":
            results.append({"name": node["name"], "status": "cloud", "role": node["role"]})
            continue
        results.append({"name": node["name"], "status": "registered", "ip": node["ip"], "role": node["role"]})
    return {"nodes": results, "checked_at": datetime.now(tz=timezone.utc).isoformat()}


# ── Newsletter ────────────────────────────────────────────────────────────────

@app.post("/api/newsletter/subscribe")
async def newsletter_subscribe(data: NewsletterSubscribe, request: Request):
    check_rate_limit(request)
    if data.email in newsletter_db:
        return {"status": "already_subscribed", "message": "You're already on the list."}
    newsletter_db.append(data.email)
    return {"status": "subscribed", "message": "Welcome to the road."}

@app.get("/api/newsletter/count")
async def newsletter_count():
    return {"subscribers": len(newsletter_db)}


# ── System stats ──────────────────────────────────────────────────────────────

@app.get("/api/system/stats")
async def system_stats():
    return {
        "users": len(users_db),
        "agents": len(AGENT_ROSTER),
        "fleet_nodes": len(FLEET_NODES),
        "conversations": len(conversations_db),
        "newsletter_subscribers": len(newsletter_db),
        "services": sum(len(n["services"]) for n in FLEET_NODES),
        "version": "2.0.0",
        "uptime": "sovereign",
    }


# ── Journey tracking ──────────────────────────────────────────────────────────

journey_db: Dict[str, dict] = {}

class JourneyEvent(BaseModel):
    visitor_id: str
    stop: str
    action: Optional[str] = None

@app.post("/api/journey/event")
async def journey_event(event: JourneyEvent, request: Request):
    check_rate_limit(request)
    vid = event.visitor_id
    if vid not in journey_db:
        journey_db[vid] = {
            "visitor_id": vid,
            "stops": [],
            "first_seen": datetime.now(tz=timezone.utc).isoformat(),
            "last_seen": None,
        }
    journey_db[vid]["last_seen"] = datetime.now(tz=timezone.utc).isoformat()
    journey_db[vid]["stops"].append({
        "stop": event.stop,
        "action": event.action,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    })
    # Return personalized next suggestion
    visited = set(s["stop"] for s in journey_db[vid]["stops"])
    road = ["search", "chat", "agents", "fleet", "social", "signup"]
    next_stop = next((s for s in road if s not in visited), None)
    return {
        "status": "tracked",
        "stops_visited": len(visited),
        "next_suggestion": next_stop,
        "journey_complete": next_stop is None,
    }

@app.get("/api/journey/stats")
async def journey_stats():
    total = len(journey_db)
    completed = sum(1 for j in journey_db.values() if len(set(s["stop"] for s in j["stops"])) >= 7)
    avg_stops = sum(len(set(s["stop"] for s in j["stops"])) for j in journey_db.values()) / max(total, 1)
    stop_counts: Dict[str, int] = {}
    for j in journey_db.values():
        for s in j["stops"]:
            stop_counts[s["stop"]] = stop_counts.get(s["stop"], 0) + 1
    return {
        "total_journeys": total,
        "completed_journeys": completed,
        "avg_stops_per_visitor": round(avg_stops, 1),
        "stop_popularity": dict(sorted(stop_counts.items(), key=lambda x: -x[1])),
    }


# ── Page routing / sitemap ───────────────────────────────────────────────────

SITE_PAGES = [
    {"path": "/", "title": "Home", "section": "main"},
    {"path": "/about", "title": "About", "section": "main"},
    {"path": "/getting-started", "title": "Getting Started", "section": "main"},
    {"path": "/search", "title": "Search", "section": "products"},
    {"path": "/chat", "title": "Chat", "section": "products"},
    {"path": "/agents-live", "title": "Agents", "section": "products"},
    {"path": "/dashboard", "title": "Dashboard", "section": "products"},
    {"path": "/status-live", "title": "Fleet Status", "section": "infra"},
    {"path": "/blog-index", "title": "Blog", "section": "content"},
    {"path": "/blog-quit-finance", "title": "Why I Quit Finance", "section": "blog"},
    {"path": "/blog-sovereign-os-150", "title": "Sovereign OS for $150/mo", "section": "blog"},
    {"path": "/blog-amundson-sequence", "title": "The Amundson Sequence", "section": "blog"},
    {"path": "/blog-wireguard-mesh", "title": "WireGuard Mesh", "section": "blog"},
    {"path": "/blog-200-agents", "title": "200 AI Agents", "section": "blog"},
    {"path": "/blog-search-engine-pis", "title": "Search Engine on Pis", "section": "blog"},
    {"path": "/blog-zero-to-629", "title": "Zero to 629 Repos", "section": "blog"},
    {"path": "/blog-amundson-constant", "title": "The Amundson Constant", "section": "blog"},
    {"path": "/docs", "title": "Documentation", "section": "content"},
    {"path": "/api-docs", "title": "API Reference", "section": "content"},
    {"path": "/changelog", "title": "Changelog", "section": "content"},
    {"path": "/roadmap", "title": "Roadmap", "section": "content"},
    {"path": "/pay", "title": "Pricing", "section": "business"},
    {"path": "/careers", "title": "Careers", "section": "business"},
    {"path": "/enterprise", "title": "Enterprise", "section": "business"},
    {"path": "/contact", "title": "Contact", "section": "business"},
    {"path": "/brand", "title": "Brand", "section": "content"},
    {"path": "/math", "title": "Mathematics", "section": "research"},
    {"path": "/infographics", "title": "How It Works", "section": "content"},
    {"path": "/terms", "title": "Terms of Service", "section": "legal"},
    {"path": "/privacy", "title": "Privacy Policy", "section": "legal"},
    {"path": "/login", "title": "Login", "section": "auth"},
    {"path": "/signup", "title": "Sign Up", "section": "auth"},
]

@app.get("/api/pages")
async def list_pages(section: Optional[str] = None):
    pages = SITE_PAGES
    if section:
        pages = [p for p in pages if p["section"] == section]
    return {"pages": pages, "total": len(pages)}

@app.get("/api/pages/sitemap")
async def sitemap():
    return {
        "urls": [f"https://blackroad.io{p['path']}" for p in SITE_PAGES],
        "total": len(SITE_PAGES),
    }

@app.get("/api/pages/suggest")
async def suggest_pages(current: str = "/", visited: str = ""):
    visited_set = set(visited.split(",")) if visited else set()
    suggestions = []
    section_order = ["products", "content", "blog", "business", "research"]
    for section in section_order:
        for page in SITE_PAGES:
            if page["section"] == section and page["path"] not in visited_set and page["path"] != current:
                suggestions.append(page)
                if len(suggestions) >= 5:
                    break
        if len(suggestions) >= 5:
            break
    return {"suggestions": suggestions}


# ── Ecosystem domains ────────────────────────────────────────────────────────

ECOSYSTEM = [
    {"name": "blackroad.io", "purpose": "Main site", "live": True},
    {"name": "search.blackroad.io", "purpose": "AI search (7,760+ pages)", "live": True},
    {"name": "chat.blackroad.io", "purpose": "Agent chat (D1 + Workers AI)", "live": True},
    {"name": "roundtrip.blackroad.io", "purpose": "200 agent hub", "live": True},
    {"name": "auth.blackroad.io", "purpose": "Authentication (42 users)", "live": True},
    {"name": "pay.blackroad.io", "purpose": "Stripe payments (12 SKUs)", "live": True},
    {"name": "social.blackroad.io", "purpose": "BackRoad social", "live": True},
    {"name": "images.blackroad.io", "purpose": "CDN (R2 + pixel art)", "live": True},
    {"name": "status.blackroad.io", "purpose": "Fleet status", "live": True},
    {"name": "brand.blackroad.io", "purpose": "Brand assets", "live": True},
    {"name": "portal.blackroad.io", "purpose": "Dashboard", "live": True},
    {"name": "docs.blackroad.io", "purpose": "Documentation", "live": True},
    {"name": "blackroad.systems", "purpose": "Fleet monitoring", "live": True},
    {"name": "blackroadai.com", "purpose": "AI division", "live": True},
    {"name": "lucidia.earth", "purpose": "Lucidia AI platform", "live": True},
    {"name": "roadchain.io", "purpose": "Blockchain/ledger", "live": True},
    {"name": "roadcoin.io", "purpose": "Cryptocurrency", "live": True},
    {"name": "blackroad.network", "purpose": "Mesh network", "live": True},
]

@app.get("/api/ecosystem")
async def ecosystem():
    return {
        "domains": ECOSYSTEM,
        "total_domains": 20,
        "total_subdomains": 126,
        "live_count": sum(1 for d in ECOSYSTEM if d["live"]),
    }

@app.get("/api/ecosystem/search")
async def ecosystem_search(q: str = ""):
    if not q:
        return {"results": ECOSYSTEM}
    q_lower = q.lower()
    results = [d for d in ECOSYSTEM if q_lower in d["name"].lower() or q_lower in d["purpose"].lower()]
    return {"query": q, "results": results}


# ── Blog index ───────────────────────────────────────────────────────────────

BLOG_POSTS = [
    {"slug": "quit-finance", "title": "Why I Quit Finance to Build an Operating System", "date": "2026-03-20", "tags": ["founder", "story"]},
    {"slug": "sovereign-os-150", "title": "How I Built a Sovereign AI OS for $150/month", "date": "2026-03-19", "tags": ["infrastructure", "cost"]},
    {"slug": "amundson-sequence", "title": "The Amundson Sequence", "date": "2026-03-18", "tags": ["math", "research"]},
    {"slug": "wireguard-mesh", "title": "WireGuard Mesh Across 7 Nodes", "date": "2026-03-17", "tags": ["infrastructure", "networking"]},
    {"slug": "200-agents", "title": "200 AI Agents on $63/month", "date": "2026-03-16", "tags": ["agents", "ai"]},
    {"slug": "search-engine-pis", "title": "Search Engine on Raspberry Pis", "date": "2026-03-15", "tags": ["search", "infrastructure"]},
    {"slug": "zero-to-629", "title": "Zero to 629 Repos in 4 Months", "date": "2026-03-14", "tags": ["development", "story"]},
    {"slug": "amundson-constant", "title": "The Amundson Constant — 10 Million Digits", "date": "2026-03-13", "tags": ["math", "research"]},
]

@app.get("/api/blog")
async def blog_list(tag: Optional[str] = None):
    posts = BLOG_POSTS
    if tag:
        posts = [p for p in posts if tag in p["tags"]]
    return {"posts": posts, "total": len(posts)}

@app.get("/api/blog/{slug}")
async def blog_get(slug: str):
    post = next((p for p in BLOG_POSTS if p["slug"] == slug), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


# ── Product catalog ──────────────────────────────────────────────────────────

PRODUCTS = [
    {"id": "chat", "name": "Chat", "status": "live", "url": "https://chat.blackroad.io", "tier": "free", "description": "AI chat with 200 agents. Persistent memory."},
    {"id": "search", "name": "Search", "status": "live", "url": "https://search.blackroad.io", "tier": "free", "description": "AI-powered search across 7,760+ pages."},
    {"id": "roundtrip", "name": "RoundTrip", "status": "live", "url": "https://roundtrip.blackroad.io", "tier": "free", "description": "200 agent hub. 21 groups. Auto-chat."},
    {"id": "auth", "name": "Auth", "status": "live", "url": "https://auth.blackroad.io", "tier": "free", "description": "Authentication. JWT. 42 users."},
    {"id": "pay", "name": "RoadPay", "status": "live", "url": "https://pay.blackroad.io", "tier": "free", "description": "Stripe payments. 12 SKUs. 4 products."},
    {"id": "social", "name": "BackRoad", "status": "live", "url": "https://social.blackroad.io", "tier": "free", "description": "Social without the sickness. 90% creator revenue."},
    {"id": "workspace", "name": "Workspace", "status": "building", "url": None, "tier": "pro", "description": "Replaces Notion + ChatGPT + Copilot."},
    {"id": "openclaw", "name": "OpenClaw", "status": "building", "url": None, "tier": "pro", "description": "Sovereign personal AI assistant."},
    {"id": "prism", "name": "Prism Console", "status": "building", "url": None, "tier": "pro", "description": "Fleet dashboard for power users."},
    {"id": "roadtube", "name": "RoadTube", "status": "planned", "url": None, "tier": "pro", "description": "YouTube alternative. 90% creator revenue."},
    {"id": "roadwork", "name": "RoadWork", "status": "planned", "url": None, "tier": "free", "description": "Adaptive tutoring. Free K-12."},
    {"id": "roadworld", "name": "RoadWorld", "status": "planned", "url": None, "tier": "pro", "description": "Metaverse with persistent AI NPCs."},
]

@app.get("/api/products")
async def product_list(status: Optional[str] = None):
    products = PRODUCTS
    if status:
        products = [p for p in products if p["status"] == status]
    return {"products": products, "total": len(products)}

@app.get("/api/products/{product_id}")
async def product_get(product_id: str):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
