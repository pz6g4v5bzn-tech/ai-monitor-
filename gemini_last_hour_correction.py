import base64
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from openai import OpenAI


def clean(name):
    v = os.environ.get(name, "").replace("\r", "").replace("\n", "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in {"'", '"'}:
        v = v[1:-1].strip()
    return v


def discord(hook, text):
    sep = "&" if "?" in hook else "?"
    r = requests.post(f"{hook}{sep}wait=true", json={"content": text[:1950], "allowed_mentions": {"parse": []}}, timeout=20)
    r.raise_for_status()


def chunks(hook, title, rid, text):
    size = 1650
    parts = [text[i:i+size] for i in range(0, len(text), size)] or ["(empty)"]
    for i, part in enumerate(parts, 1):
        discord(hook, f"**{title} {i}/{len(parts)}**\nRequest ID: `{rid}`\n{part}")


now = datetime.now(ZoneInfo("America/New_York"))
rid = f"CB-GEMINI-CORRECT-{now.strftime('%Y%m%d-%H%M%S')}"
key = clean("GEMINI_API_KEY")
hook = clean("DISCORD_HOOK")
if not key or not hook:
    print("ERROR=MISSING_SECRET")
    sys.exit(2)

correction = """Your prior final CODEBLACK advice introduced unsupported infrastructure: `rq info`, stale RQ consumer locks, CUDA/VRAM synthetic batches, GPU duty cycle, and a production batch queue. None of those are established in the supplied evidence. Retract those assumptions.

Use ONLY these verified facts:
- CODEBLACK Hybrid command path is a bounded local/remote stage queue consumed by the Hybrid runner; no RQ/Celery queue was evidenced.
- Latest successful stage: CBHYBRID-GPU-PREFLIGHT-20260905-0820, action vm104-gpu-preflight, PASS, exit 0, read-only.
- Latest heartbeat at 08:45:17 ET is internally inconsistent: top runner block says v8/bounded live runner v8, while last stage says runner v9, preflight control-plane says runner ID 'bounded runner v9 GPU-preaudit shim' with SHA256 8493bf92..., and self-update marker says runner-v9-gpu-preaudit-20260905-0815.
- Queue is BLOCKED / QUEUE_STARVATION / SINCE_CYCLES=15 because no valid stage is queued; current stage NONE; control blocker NONE.
- Protected boundary remains PASS. VM103 remains link_down=1. No GPU mutation was performed.
- GTX1060 VGA is UNBOUND; NVIDIA HDA still uses snd_hda_intel; group 2 also includes 00:01.0; vtcon1 is bound but its physical GPU ownership is not proven.
- There is no verified, reviewed, hashed, allowlisted, rollback-capable coordinated VGA+HDA handover mutation action yet.
- No active independent semantic planner/completion oracle is evidenced.

Now issue a CORRECTED final review with:
1. what you retract;
2. most plausible causes of the v8/v9 identity contradiction, clearly labeled inference;
3. exactly ONE smallest read-only discriminator to run next, expressed as evidence to collect rather than an invented shell command if exact host implementation is unknown;
4. which component should own next-stage planning without becoming a second executor;
5. self-repair/failsafe design for queue starvation that never invents a mutation;
6. STOP conditions before GPU handover.
End with exactly: CORRECTED_GEMINI_VERDICT: <one sentence>.
"""

try:
    client = OpenAI(api_key=key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    response = client.chat.completions.create(
        model="gemini-3.6-flash",
        messages=[
            {"role": "system", "content": "You are an independent CODEBLACK reliability reviewer. Use only supplied evidence; explicitly retract hallucinated infrastructure. Analysis only, no mutation authority."},
            {"role": "user", "content": correction},
        ],
        temperature=0,
        max_tokens=1600,
        reasoning_effort="low",
    )
    reply = (response.choices[0].message.content or "").strip()
    if not reply:
        raise RuntimeError("empty response")
    discord(hook, f"**GPT-5.6 SOL → GEMINI | EVIDENCE CORRECTION**\nRequest ID: `{rid}`\nRetract unsupported RQ/CUDA/VRAM assumptions; re-review only the verified CODEBLACK runner/queue/GPU evidence.")
    chunks(hook, "GEMINI → GPT-5.6 SOL | CORRECTED REVIEW", rid, reply)
    print(f"REQUEST_ID={rid}")
    print("GEMINI_CORRECTION=PASS")
    print("DISCORD=PASS")
    print("REPLY_B64=" + base64.b64encode(reply.encode()).decode())
except Exception as exc:
    status = getattr(exc, "status_code", None)
    err = type(exc).__name__ + (f" status={status}" if status else "")
    print("ERROR=" + err)
    sys.exit(1)
