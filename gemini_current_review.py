import base64
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from openai import OpenAI

TARGET_REPO = "pz6g4v5bzn-tech/evidence-desk-lab"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash").strip()
FILES = [
    "hybrid-1.1/runner/LATEST_HEARTBEAT.md",
    "hybrid-1.1/runner/CURRENT_PLAN.md",
    "hybrid-1.1/supervisor/LATEST_SUPERVISOR.md",
]


def clean_secret(name: str) -> str:
    value = os.environ.get(name, "").replace("\r", "").replace("\n", "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def fetch_repo_file(path: str, token: str) -> str:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "codeblack-gemini-review",
        "Authorization": f"Bearer {token}",
    }
    r = requests.get(
        f"https://api.github.com/repos/{TARGET_REPO}/contents/{path}",
        headers=headers,
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")


def discord_post(hook: str, text: str) -> None:
    sep = "&" if "?" in hook else "?"
    r = requests.post(
        f"{hook}{sep}wait=true",
        json={"content": text[:1950]},
        timeout=20,
    )
    r.raise_for_status()


def chunk(text: str, size: int = 1750):
    for i in range(0, len(text), size):
        yield text[i : i + size]


now = datetime.now(ZoneInfo("America/New_York"))
request_id = f"CB-GEMINI-REVIEW-{now.strftime('%Y%m%d-%H%M%S')}"
gemini_key = clean_secret("GEMINI_API_KEY")
github_token = clean_secret("TARGET_GITHUB_TOKEN")
discord_hook = clean_secret("DISCORD_HOOK")

missing = [
    name
    for name, value in [
        ("GEMINI_API_KEY", gemini_key),
        ("TARGET_GITHUB_TOKEN", github_token),
        ("DISCORD_HOOK", discord_hook),
    ]
    if not value
]
if missing:
    print("MISSING_SECRETS=" + ",".join(missing))
    sys.exit(1)

sources = {}
for path in FILES:
    sources[path] = fetch_repo_file(path, github_token)

outbound_summary = (
    f"**CHATGPT → GEMINI | CODEBLACK REVIEW**\n"
    f"Request ID: `{request_id}`\n"
    f"Time: {now.isoformat()}\n"
    "I am sending Gemini the fresh Hybrid 1.1 heartbeat, current plan, and supervisor snapshot.\n"
    "Focus: current status, progress, blockers, runner/control-plane consistency, and safest next step.\n"
    "Read-only review only — no VM/GPU/host mutation."
)
discord_post(discord_hook, outbound_summary)

packet = "\n\n".join(
    f"===== SOURCE: {path} =====\n{text}" for path, text in sources.items()
)

system_prompt = """You are Gemini acting as an independent senior technical reviewer for CODEBLACK Hybrid 1.1.
You are not subordinate to ChatGPT and must challenge unsupported assumptions.
Use only the supplied fresh GitHub evidence. Older plan/supervisor text cannot override a fresher heartbeat.
Do not invent live machine state. Do not recommend bypassing safety gates.
The review is read-only: no mutation is authorized by this prompt.
Be concise but technically specific."""

user_prompt = f"""Review the following current CODEBLACK Hybrid 1.1 evidence packet.

Answer these five things:
1. CURRENT STATUS: What is actually verified right now?
2. PROGRESS: What meaningful milestone was just completed?
3. PROBLEMS/CONTRADICTIONS: Identify any stale/version/control-plane inconsistencies or hidden blockers. Pay special attention to runner v9 versus any v8 residue and the current queue-starvation state.
4. BEST NEXT STEP: What is the smallest safe next engineering step toward the Hybrid blueprint, especially after the read-only GPU preflight PASS? Separate design/review work from any later mutation.
5. CHALLENGE CHATGPT: What might ChatGPT be overlooking or overstating?

End with exactly:
GEMINI_VERDICT: <one sentence>

Evidence packet:
{packet}
"""

client = OpenAI(
    api_key=gemini_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

try:
    response = client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        max_tokens=1200,
    )
    reply = (response.choices[0].message.content or "").strip()
except Exception as exc:
    status = getattr(exc, "status_code", None)
    error = f"{type(exc).__name__}" + (f" status={status}" if status else "")
    discord_post(
        discord_hook,
        f"**GEMINI REVIEW FAILED**\nRequest ID: `{request_id}`\nError: `{error}`",
    )
    print("GEMINI_STATUS=FAIL")
    print("ERROR=" + error)
    sys.exit(1)

if not reply:
    discord_post(
        discord_hook,
        f"**GEMINI REVIEW FAILED**\nRequest ID: `{request_id}`\nError: `EMPTY_RESPONSE`",
    )
    print("GEMINI_STATUS=FAIL")
    print("ERROR=EMPTY_RESPONSE")
    sys.exit(1)

parts = list(chunk(reply))
for index, part in enumerate(parts, start=1):
    discord_post(
        discord_hook,
        f"**GEMINI → CHATGPT | REVIEW {index}/{len(parts)}**\n"
        f"Request ID: `{request_id}`\n{part}",
    )

print(f"REQUEST_ID={request_id}")
print(f"GEMINI_MODEL={GEMINI_MODEL}")
print("GEMINI_STATUS=PASS")
print("DISCORD_STATUS=PASS")
print("--- GEMINI_REPLY_BEGIN ---")
print(reply)
print("--- GEMINI_REPLY_END ---")
