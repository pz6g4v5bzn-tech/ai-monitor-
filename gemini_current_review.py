import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from openai import OpenAI

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash").strip()


def clean_secret(name: str) -> str:
    value = os.environ.get(name, "").replace("\r", "").replace("\n", "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


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
discord_hook = clean_secret("DISCORD_HOOK")

if not gemini_key or not discord_hook:
    print("MISSING_SECRET")
    sys.exit(1)

# Sanitized, current evidence retrieved through the authorized ChatGPT GitHub
# connector immediately before this workflow was committed. No credentials,
# webhook URLs, private tokens, or unrelated Drive data are included.
packet = """CODEBLACK Hybrid 1.1 — CURRENT EVIDENCE PACKET
Evidence time: 2026-09-05 08:30 America/New_York
Authoritative runtime source: hybrid-1.1/runner/LATEST_HEARTBEAT.md

CURRENT RUNTIME
- Heartbeat v2 timestamp: 2026-09-05T08:30:09-04:00.
- Canonical runner: v9, ID 'CODEBLACK Hybrid 1.1 — bounded runner v9 GPU-preaudit shim'.
- Runner release: hybrid-runner-v9-gpu-preaudit-20260905-0815.
- Runner SHA256: 8493bf92a18f8fbdaff3a5922c086dae4107331f54c37dff156b3c155c54d2cc.
- VM104 helper: hybrid-vm104-helper-v8-gpu-preaudit-20260905-0810.
- Current stage: NONE.
- Control blocker: NONE.

LATEST COMPLETED STAGE
- request_id: CBHYBRID-GPU-PREFLIGHT-20260905-0820
- action: vm104-gpu-preflight
- status: PASS
- exit: 0
- end: 2026-09-05T08:24:02-04:00
- stage-log SHA256: 8c423a10ca0b441f0df50d85be48727f8e8b47a932943ddcae5d2a1f2a972304
- This was READ-ONLY evidence collection. No GPU/VM/host mutation occurred.

FRESH SAFETY/PREFLIGHT STATE
- PROTECTED_BOUNDARY=PASS
- VM100=running; recovery path 1 PASS
- VM101=stopped/protected
- VM102=stopped/protected
- VM103=running, net0 link_down=1; recovery path 2 PASS
- VM104=running
- IOMMU groups PASS; media SHA256 gate PASS
- GTX1060 VGA 0000:01:00.0 [10de:1c03] is UNBOUND
- NVIDIA HDA 0000:01:00.1 [10de:10f1] uses snd_hda_intel
- Both NVIDIA functions are in IOMMU group 2
- vtcon1 is a bound framebuffer device
- VM103 must never receive either NVIDIA function.

CURRENT QUEUE/STALL STATE
- Queue status at 08:30 is BLOCKED / QUEUE_STARVATION / SINCE_CYCLES=4.
- Detail: no valid local or remote stage is queued; advancement requires a new validated stage or verified completion marker.
- IMPORTANT inconsistency: that queue-starvation block embeds RUNNER_VERSION=v8 even though the fresh canonical runner identity is v9.

PLAN/SUPERVISOR STALENESS
- CURRENT_PLAN.md was updated 08:24:46 and still describes the GPU preflight as queued/waiting.
- Fresh 08:30 heartbeat supersedes that: the GPU preflight already PASSed at 08:24:02.
- Supervisor snapshot is also older and says the same job is only queued.
- Therefore runtime heartbeat is the truth; plan/supervisor text needs reconciliation.

MEANINGFUL PROGRESS
- Virtual Hybrid baseline is complete and VM104 is running.
- Protected preflight/recovery gates are PASS.
- Helper v8 GPU-preaudit capability is installed.
- Runner v9 GPU-preaudit shim is installed and now canonically identified by heartbeat.
- Read-only coordinated GPU/HDA preaudit completed PASS.
- OpenAI↔Gemini Flash↔Discord monitoring path has separately been proven end-to-end in ai-monitor-; it is advisory and does not execute VM/host mutations.

KNOWN CONTROL-PLANE GAPS
- No active independent on-host semantic planner/completion oracle is evidenced.
- No separately evidenced active independent supervisor/recovery-controller/bidirectional-broker daemon exists yet; repository supervisor documents are summaries/policy.
- The issue-based executor route was previously degraded; the verified Hybrid command path is still the bounded file queue/runner path.
- The next mutation-capable coordinated VGA+HDA handover action does not yet exist as a reviewed, versioned, hashed, allowlisted, rollback-capable runner/helper capability.

CURRENT INTENDED NEXT RULE
- Do not perform GPU mutation merely because preaudit passed.
- First reconcile stale v8/v9 control-plane metadata.
- Then design/review the smallest coordinated VGA+HDA handover implementation with exact prerequisites, rollback, bounded timeout, one-stage semantics and post-handover verification.
- Only after that implementation itself is installed and verified through the bounded self-update path should any hardware handover be considered.
"""

outbound_summary = (
    f"**CHATGPT → GEMINI | CODEBLACK CURRENT REVIEW**\n"
    f"Request ID: `{request_id}`\n"
    f"Time: {now.isoformat()}\n"
    "Sent: fresh status, GPU-preflight PASS, queue starvation, v9/v8 residue, progress and control-plane gaps.\n"
    "Mode: READ-ONLY analysis. Watch this Discord channel for Gemini's reply."
)
discord_post(discord_hook, outbound_summary)

system_prompt = """You are Gemini acting as an independent senior technical reviewer for CODEBLACK Hybrid 1.1.
You are not subordinate to ChatGPT. Challenge unsupported assumptions and identify contradictions.
Use only the supplied evidence packet. Do not invent live machine state.
Do not recommend bypassing safety gates. This prompt authorizes analysis only, not mutation.
Be concise but technically specific."""

user_prompt = f"""Analyze this current CODEBLACK Hybrid 1.1 state.

Answer:
1. CURRENT STATUS — what is actually verified now?
2. PROGRESS — what important milestone was just completed?
3. PROBLEMS — identify stale/version/control-plane inconsistencies and the real reason advancement is blocked.
4. BEST NEXT STEP — give the smallest safe engineering plan after GPU preflight PASS. Clearly separate metadata repair, implementation/review, and any later hardware mutation.
5. CHALLENGE CHATGPT — what might ChatGPT be overlooking, overstating, or sequencing incorrectly?

Pay special attention to:
- canonical runner v9 versus RUNNER_VERSION=v8 inside QUEUE_STARVATION,
- stale plan/supervisor text that still says the already-passed preflight is queued,
- GTX1060 VGA unbound while NVIDIA HDA remains on snd_hda_intel in the same IOMMU group,
- vtcon1 framebuffer ownership,
- absence of a currently verified mutation-capable coordinated handover action.

End exactly with:
GEMINI_VERDICT: <one sentence>

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
    discord_post(discord_hook, f"**GEMINI REVIEW FAILED**\nRequest ID: `{request_id}`\nError: `{error}`")
    print("GEMINI_STATUS=FAIL")
    print("ERROR=" + error)
    sys.exit(1)

if not reply:
    discord_post(discord_hook, f"**GEMINI REVIEW FAILED**\nRequest ID: `{request_id}`\nError: `EMPTY_RESPONSE`")
    print("GEMINI_STATUS=FAIL")
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
