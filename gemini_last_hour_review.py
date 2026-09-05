import base64
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from openai import OpenAI

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash").strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-sol").strip()


def clean_secret(name: str) -> str:
    value = os.environ.get(name, "").replace("\r", "").replace("\n", "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def discord_post(hook: str, text: str) -> None:
    sep = "&" if "?" in hook else "?"
    r = requests.post(
        f"{hook}{sep}wait=true",
        json={"content": text[:1950], "allowed_mentions": {"parse": []}},
        timeout=20,
    )
    r.raise_for_status()


def post_chunks(hook: str, heading: str, request_id: str, text: str, size: int = 1650) -> None:
    parts = [text[i:i + size] for i in range(0, len(text), size)] or ["(empty response)"]
    for idx, part in enumerate(parts, 1):
        discord_post(
            hook,
            f"**{heading} {idx}/{len(parts)}**\nRequest ID: `{request_id}`\n{part}",
        )


def gemini_call(client: OpenAI, system: str, prompt: str, max_tokens: int = 2200) -> str:
    response = client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=max_tokens,
        reasoning_effort="low",
    )
    return (response.choices[0].message.content or "").strip()


def openai_call(client: OpenAI, system: str, prompt: str, max_tokens: int = 1200) -> str:
    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=system,
        input=prompt,
        max_output_tokens=max_tokens,
    )
    return (response.output_text or "").strip()


now = datetime.now(ZoneInfo("America/New_York"))
request_id = f"CB-LAST-HOUR-{now.strftime('%Y%m%d-%H%M%S')}"
gemini_key = clean_secret("GEMINI_API_KEY")
openai_key = clean_secret("OPENAI_API_KEY")
discord_hook = clean_secret("DISCORD_HOOK")

if not gemini_key or not openai_key or not discord_hook:
    print("ERROR=MISSING_SECRET")
    sys.exit(2)

# Sanitized retrospective assembled from the authorized GitHub connector and
# GitHub Actions evidence. It contains project evidence only; no credentials,
# webhook URLs, unrelated Drive data, or private user content.
report = r"""CODEBLACK HYBRID 1.1 — LAST ONE HOUR RETROSPECTIVE
Window: approximately 2026-09-05 07:48–08:48 America/New_York
Purpose: independent technical review of progress, stalls, failures, repairs,
upgrades, agent/control-plane quality, and the safest fastest next step.

A. PROGRESS / SUCCESSFUL WORK
1. Heartbeat v2 continued publishing every ~5 minutes; protected preflight stayed PASS throughout the reviewed evidence.
2. Reporting freshness was repaired: LATEST_HEARTBEAT.md is now the authoritative dynamic runtime source; static CURRENT_PLAN/supervisor/version documents are required to defer to it and become stale for advancement after 600 seconds.
3. Google Drive Hybrid architecture was synchronized with the newer runner/helper model and clarified as design baseline, not runtime truth.
4. Canonical v8 dependent references were synchronized across control-plane artifacts before the next upgrade.
5. VM104 helper v8 GPU-preaudit capability was staged, approved, then machine-verified installed. It adds read-only GPU pre-handover evidence only.
6. Runner v9 GPU-preaudit shim was staged/approved over the verified v8 base. An unapproved duplicate v9 candidate was removed rather than allowed to race the canonical payload.
7. A single read-only GPU preflight job was queued: CBHYBRID-GPU-PREFLIGHT-20260905-0820 / vm104-gpu-preflight.
8. That stage completed PASS, exit=0 at 08:24:02 ET. Stage log SHA256: 8c423a10ca0b441f0df50d85be48727f8e8b47a932943ddcae5d2a1f2a972304. The processed PASS queue entry was then cleared.
9. Fresh safety evidence remained: VM100 running/recovery PASS; VM101/VM102 stopped/protected; VM103 running with link_down=1/recovery PASS; VM104 running; IOMMU PASS; Ubuntu media SHA gate PASS. No protected-VM/GPU/USB/host-network/firewall/storage-layout mutation was performed by the audit.
10. GPU audit found GTX1060 VGA 0000:01:00.0 [10de:1c03] UNBOUND; NVIDIA HDA 0000:01:00.1 [10de:10f1] still on snd_hda_intel. Both are in IOMMU group 2, and 00:01.0 is also in group 2. vtcon1 is a bound framebuffer device, but evidence does not yet prove which physical GPU owns it.
11. The separate AI monitoring path was repaired and proven end-to-end: GPT-5.6 Sol PASS, Gemini 3.6 Flash PASS, Gemini follow-up PASS, Discord PASS.
12. An event-driven Gemini/OpenAI reviewer was installed into the private main project repository. It detects significant pushes, issues/comments, PR activity, CI completion, version/SHA changes, PASS/FAIL/BLOCKED/stalls and important plan/evidence changes; timestamp-only heartbeat churn is filtered.

B. STALL / HALT / FREEZE STATE
1. No verified runner process freeze is shown in the latest evidence. The active blockage is QUEUE_STARVATION: no valid next local or remote stage is queued.
2. At 08:30 queue starvation was 4 cycles. By the 08:45 heartbeat it had reached SINCE_CYCLES=15. Current stage=NONE; control blocker=NONE; last stage is the successful GPU preflight.
3. Therefore the present stall is primarily a planning/next-stage gap, not evidence that the last runner action failed.

C. FAILURES / DEFECTS OBSERVED AND REPAIRS
1. Earlier AI-channel OpenAI call failed with 'Illegal header value'. Root cause: hidden CR/LF/whitespace in stored secret. Repair: normalize secrets before client construction. Verified afterward by successful GPT-5.6 Sol calls.
2. Gemini Pro experiments were not reliable for this channel: gemini-3.1-pro-preview returned HTTP 429; a gemini-2.5-pro compatibility-path retry returned HTTP 404. Rather than loop, channel returned to the previously proven gemini-3.6-flash. Production Flash path then PASSed.
3. First one-time Gemini review attempted to fetch the private main repo with ai-monitor's TARGET_GITHUB_TOKEN and got HTTP 401. Repair: do not broaden token access blindly; instead use a sanitized evidence packet retrieved through the authorized GitHub connector. Retry PASSed and Discord delivery PASSed.
4. First Gemini review response was visibly truncated. Repair: use low reasoning effort and larger visible output budget; complete review then PASSed and was delivered to Discord.
5. The first live event-driven reviewer run inside the private main repo correctly detected a HIGH project-state event but failed safe with AI_SECRETS_MISSING because OPENAI_API_KEY, GEMINI_API_KEY and DISCORD_HOOK are not yet stored there. User is adding these GitHub Actions secrets now. No secret was copied/exposed from ai-monitor.
6. Static control-plane authority drift occurred because overlapping supervisors had conflicting GPU wording. Duplicate supervisor watches were disabled/reconciled; one current authority remains. Historical evidence preserved.

D. IMPORTANT CURRENT CONTRADICTIONS / NEWEST 08:45 EVIDENCE
1. Latest heartbeat timestamp: 08:45:17 ET.
2. Top Runner identity now says RUNNER_VERSION=v8, ID='bounded live runner v8', release hybrid-runner-v8-result-queue-reporting-20260905-0600.
3. BUT that same heartbeat's last successful stage says RUNNER_VERSION=v9, its control-plane preflight says RUNNER_ID='bounded runner v9 GPU-preaudit shim' with SHA256 8493bf92a18f8fbdaff3a5922c086dae4107331f54c37dff156b3c155c54d2cc, and self-update marker says HYBRID_RUNNER=hybrid-runner-v9-gpu-preaudit-20260905-0815.
4. This is now stronger than the earlier stale v8 residue: the top heartbeat identity appears to have regressed/desynchronized after a previously observed v9 identity. Do not assume which version is actually executing until identity/reporting source is reconciled from machine evidence.
5. Queue status at 08:44:04 says BLOCKED / QUEUE_STARVATION / SINCE_CYCLES=15 / RUNNER_VERSION=v8.
6. CURRENT_PLAN and older supervisor summary had also lagged the already-completed GPU-preflight state. Runtime heartbeat remains authoritative but is itself internally inconsistent on runner identity.

E. CURRENT ENGINEERING GAP
There is still no reviewed, versioned, hashed, rollback-capable, allowlisted mutation implementation for a coordinated GTX1060 VGA + NVIDIA HDA handover to VM104. A read-only preaudit PASS is evidence, not mutation authorization or proof that passthrough is ready. Full IOMMU group viability, vtcon1 ownership, host audio impact, rollback sequence and post-handover display/audio/NVIDIA verification must be explicit.

F. QUESTIONS FOR GEMINI — BE INDEPENDENT, NOT AGREEABLE
1. What is the most plausible root cause of the v9→v8 runner-identity/reporting regression? Give the safest read-only discriminating checks before any new stage.
2. Is the current queue starvation a planner/supervisor defect, expected safe hold, or runner defect? Separate symptom, proximate cause, root cause and effect.
3. Which agent/component should own semantic next-stage generation, and how should it avoid races with the sole executor?
4. What is the fastest safe architecture for event-driven detection → diagnosis → repair plan → verification without hourly polling or retry storms?
5. What self-repair logic should be deterministic/local versus delegated to Gemini/GPT? Include timeout, dedupe, backoff, rollback and dead-man/failsafe design.
6. For the GPU handover path, what evidence is still missing? Challenge any assumption that vtcon1 belongs to the GTX1060 or that IOMMU group 2 can be passed safely just because both NVIDIA functions share it.
7. Identify any overengineering, stale metadata mechanism, weak agent responsibility or unnecessary latency in the current design.
8. Give a prioritized next-3-actions plan. Action 1 must be read-only if state identity is inconsistent.
9. State STOP conditions that must block mutation.
10. Give your opinion on how Gemini and GPT-5.6 Sol should divide work for fastest reliable problem solving, cause/effect learning, upgrades and future fail-safe behavior.
"""

gemini_system = """You are Gemini, an independent senior reliability and systems reviewer for CODEBLACK Hybrid 1.1. Do not simply agree with ChatGPT. Distinguish verified evidence from inference. Prioritize root cause, minimal safe repair, fast execution, clear agent ownership, self-repair and future failsafes. Never authorize or invent machine mutation. Be technically specific and concise enough to read in Discord."""

openai_system = """You are GPT-5.6 Sol acting as an independent reconciler. Check Gemini's review against the supplied retrospective. Correct unsupported assumptions or version mistakes. Focus on the smallest read-only discriminator, root cause, ownership, speed, reliability, self-repair and failsafes. Do not claim or execute machine changes."""

try:
    gemini_client = OpenAI(
        api_key=gemini_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    openai_client = OpenAI(api_key=openai_key)

    discord_post(
        discord_hook,
        f"**CHATGPT → GEMINI | LAST 1-HOUR CODEBLACK REPORT**\n"
        f"Request ID: `{request_id}`\n"
        f"Window: ~07:48–08:48 ET\n"
        "Sent: progress, PASS stages, queue starvation, failures/repairs, runner/helper upgrades, AI-channel incidents, GPU-preaudit evidence, latest v8/v9 identity contradiction and current gaps.\n"
        "Mode: READ-ONLY technical review."
    )

    gemini_reply = gemini_call(
        gemini_client,
        gemini_system,
        "Review the last-hour retrospective below. Give: VERIFIED STATE; SUCCESSES; FAILURES/ROOT CAUSES; CURRENT BLOCKER; BEST AGENT OWNERSHIP; FASTEST SAFE NEXT 3 ACTIONS; SELF-REPAIR/FAILSAFE UPGRADES; WHAT CHATGPT MAY BE MISSING; STOP CONDITIONS; and a one-sentence GEMINI_VERDICT.\n\n" + report,
    )
    if not gemini_reply:
        raise RuntimeError("Gemini returned empty response")
    post_chunks(discord_hook, "GEMINI → CHATGPT | 1-HOUR REVIEW", request_id, gemini_reply)

    gpt_reply = openai_call(
        openai_client,
        openai_system,
        "Here is the evidence retrospective:\n\n" + report + "\n\nHere is Gemini's review:\n\n" + gemini_reply + "\n\nVerify/challenge Gemini. Return concise corrections, agreements supported by evidence, the smallest read-only next discriminator, and the best ownership/failsafe design. End with GPT_VERDICT: <one sentence>.",
    )
    if not gpt_reply:
        raise RuntimeError("OpenAI returned empty response")
    post_chunks(discord_hook, "GPT-5.6 SOL → GEMINI | VERIFICATION", request_id, gpt_reply)

    gemini_final = gemini_call(
        gemini_client,
        gemini_system,
        "You previously reviewed the evidence. GPT-5.6 Sol responded as follows:\n\n" + gpt_reply + "\n\nNow give a FINAL JOINT-REVIEW RESPONSE. Accept corrections that are evidence-supported, disagree where necessary, and give exactly the safest fastest next 3 actions with owner, verification and STOP condition. End with FINAL_GEMINI_ADVICE: <one sentence>.",
        max_tokens=1600,
    )
    if not gemini_final:
        raise RuntimeError("Gemini final returned empty response")
    post_chunks(discord_hook, "GEMINI → GPT-5.6 SOL | FINAL ADVICE", request_id, gemini_final)

    print(f"REQUEST_ID={request_id}")
    print("GEMINI_INITIAL=PASS")
    print("OPENAI_RECONCILE=PASS")
    print("GEMINI_FINAL=PASS")
    print("DISCORD=PASS")
    print("GEMINI_FINAL_B64=" + base64.b64encode(gemini_final.encode()).decode())
except Exception as exc:
    status = getattr(exc, "status_code", None)
    err = type(exc).__name__ + (f" status={status}" if status else "")
    try:
        discord_post(discord_hook, f"**LAST-HOUR REVIEW FAILED**\nRequest ID: `{request_id}`\nError: `{err}`")
    except Exception:
        pass
    print("ERROR=" + err)
    sys.exit(1)
