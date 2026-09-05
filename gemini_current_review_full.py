import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from openai import OpenAI


def clean_secret(name: str) -> str:
    v = os.environ.get(name, "").replace("\r", "").replace("\n", "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in {"'", '"'}:
        v = v[1:-1].strip()
    return v


def post_discord(hook: str, text: str) -> None:
    sep = "&" if "?" in hook else "?"
    r = requests.post(f"{hook}{sep}wait=true", json={"content": text[:1950]}, timeout=20)
    r.raise_for_status()


def chunks(text: str, n: int = 1700):
    return [text[i:i+n] for i in range(0, len(text), n)]


key = clean_secret("GEMINI_API_KEY")
hook = clean_secret("DISCORD_HOOK")
if not key or not hook:
    print("MISSING_SECRET")
    sys.exit(1)

now = datetime.now(ZoneInfo("America/New_York"))
request_id = f"CB-GEMINI-FULL-{now.strftime('%Y%m%d-%H%M%S')}"

facts = """Fresh CODEBLACK Hybrid 1.1 evidence, 2026-09-05 08:30 America/New_York:

RUNTIME
- Heartbeat v2: 08:30:09 EDT, read-only evidence.
- Canonical runner v9, release hybrid-runner-v9-gpu-preaudit-20260905-0815, SHA256 8493bf92a18f8fbdaff3a5922c086dae4107331f54c37dff156b3c155c54d2cc.
- VM104 helper v8 GPU-preaudit installed.
- Current stage NONE; control blocker NONE.

LATEST STAGE
- CBHYBRID-GPU-PREFLIGHT-20260905-0820 / vm104-gpu-preflight = PASS, exit 0 at 08:24:02.
- Stage log SHA256 8c423a10ca0b441f0df50d85be48727f8e8b47a932943ddcae5d2a1f2a972304.
- This stage was read-only; no hardware or VM mutation occurred.

SAFETY
- PROTECTED_BOUNDARY PASS.
- VM100 running; recovery path PASS.
- VM101/VM102 stopped and protected.
- VM103 running with link_down=1; recovery path PASS; it must never receive GTX1060/HDA.
- VM104 running.
- IOMMU and media gates PASS.

GPU/HDA
- GTX1060 VGA 01:00.0 [10de:1c03] is UNBOUND.
- NVIDIA HDA 01:00.1 [10de:10f1] remains on snd_hda_intel.
- Both are IOMMU group 2.
- vtcon1 is still a bound framebuffer device.

CURRENT BLOCK
- Queue is BLOCKED / QUEUE_STARVATION, cycles=4: no next validated stage exists.
- The QUEUE_STARVATION block incorrectly says RUNNER_VERSION=v8 although fresh canonical identity is v9.
- CURRENT_PLAN and supervisor snapshot are stale: they still describe the GPU preflight as queued even though fresh heartbeat proves it PASSed.

PROGRESS
- Virtual Hybrid baseline complete.
- Recovery/protected gates PASS.
- Helper v8 GPU-preaudit installed.
- Runner v9 installed and canonically reported.
- Coordinated GPU/HDA read-only preaudit PASS.

GAPS
- No verified independent semantic planner/completion oracle.
- No separately verified active independent supervisor/recovery-controller/bidirectional-broker daemon.
- No reviewed/versioned/hashed/allowlisted/rollback-capable coordinated VGA+HDA handover mutation action exists yet.
- Therefore PASS preaudit is evidence only, not authorization or implementation readiness for passthrough.
"""

prompt = f"""You are the independent senior reviewer. Answer directly; do not show chain-of-thought.
Use only the evidence below. Challenge ChatGPT where warranted. Do not invent live facts and do not bypass safety gates.

Give exactly these sections, concise but complete:
1. CURRENT STATUS
2. PROGRESS
3. REAL BLOCKERS / CONTRADICTIONS
4. SAFEST NEXT ENGINEERING SEQUENCE (numbered, design/review first; mutation later only if prerequisites pass)
5. WHAT CHATGPT MAY BE MISSING
6. GEMINI_VERDICT: one sentence

Important questions:
- Must the stale v8 queue metadata and stale plan/supervisor state be reconciled before any consequential GPU step?
- Given VGA is unbound but HDA is still snd_hda_intel and vtcon1 remains bound, what additional evidence/design is required before coordinated handover?
- Is current QUEUE_STARVATION a runner failure or a missing-next-stage/planning failure?

{facts}
"""

post_discord(
    hook,
    f"**CHATGPT → GEMINI | FULL CURRENT REVIEW**\nRequest ID: `{request_id}`\n"
    "Fresh Hybrid status/progress/blockers sent. Read-only. Gemini is reviewing now."
)

client = OpenAI(api_key=key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
try:
    response = client.chat.completions.create(
        model="gemini-3.6-flash",
        reasoning_effort="low",
        messages=[
            {"role": "system", "content": "Independent CODEBLACK technical reviewer. Be evidence-bound, skeptical, concise, and safe."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=4096,
    )
    reply = (response.choices[0].message.content or "").strip()
except Exception as exc:
    status = getattr(exc, "status_code", None)
    err = f"{type(exc).__name__}" + (f" status={status}" if status else "")
    post_discord(hook, f"**GEMINI REVIEW FAILED**\n`{request_id}`\n`{err}`")
    print("GEMINI_STATUS=FAIL")
    print("ERROR=" + err)
    sys.exit(1)

if not reply:
    post_discord(hook, f"**GEMINI REVIEW FAILED**\n`{request_id}`\n`EMPTY_RESPONSE`")
    sys.exit(1)

parts = chunks(reply)
for i, part in enumerate(parts, 1):
    post_discord(hook, f"**GEMINI → CHATGPT | {i}/{len(parts)}**\nRequest ID: `{request_id}`\n{part}")

# Base64 is printed as one line so the complete reply can be independently recovered from Actions logs.
import base64
encoded = base64.b64encode(reply.encode("utf-8")).decode("ascii")
print(f"REQUEST_ID={request_id}")
print("GEMINI_STATUS=PASS")
print("DISCORD_STATUS=PASS")
print("GEMINI_REPLY_B64=" + encoded)
