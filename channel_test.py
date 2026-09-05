import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from openai import OpenAI

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-sol").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview").strip()


def clean_secret(name: str) -> str:
    value = os.environ.get(name, "")
    value = value.replace("\r", "").replace("\n", "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def safe_error(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)
    parts = [type(exc).__name__]
    if status is not None:
        parts.append(f"status={status}")
    if code:
        parts.append(f"code={code}")
    return " ".join(parts)


def openai_text(client: OpenAI, prompt: str) -> str:
    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt,
        max_output_tokens=120,
    )
    return (response.output_text or "").strip()


def gemini_text(client: OpenAI, prompt: str) -> str:
    response = client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the Gemini Pro side of a private AI channel health test. "
                    "Follow the requested reply format exactly and do not expose secrets."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=120,
    )
    return (response.choices[0].message.content or "").strip()


now = datetime.now(ZoneInfo("America/New_York"))
request_id = f"CB-AI-TEST-{now.strftime('%Y%m%d-%H%M%S')}"

openai_key = clean_secret("OPENAI_API_KEY")
gemini_key = clean_secret("GEMINI_API_KEY")
discord_hook = clean_secret("DISCORD_HOOK")

openai_status = "FAIL"
gemini_status = "FAIL"
verify_status = "FAIL"
discord_status = "FAIL"

openai_reply = ""
gemini_reply = ""
verify_reply = ""
errors = []

if not openai_key:
    errors.append("OPENAI=MISSING_SECRET")
else:
    try:
        openai_client = OpenAI(api_key=openai_key)
        openai_reply = openai_text(
            openai_client,
            (
                "CODEBLACK AI CHANNEL END-TO-END TEST. "
                f"Request ID: {request_id}. "
                "Reply exactly with OPENAI_CHANNEL_OK."
            ),
        )
        openai_status = "PASS" if "OPENAI_CHANNEL_OK" in openai_reply else "FAIL"
        if openai_status != "PASS":
            errors.append("OPENAI=UNEXPECTED_REPLY")
    except Exception as exc:
        errors.append(f"OPENAI={safe_error(exc)}")

if not gemini_key:
    errors.append("GEMINI=MISSING_SECRET")
else:
    try:
        gemini_client = OpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        gemini_reply = gemini_text(
            gemini_client,
            (
                "CODEBLACK AI CHANNEL END-TO-END TEST.\n"
                f"Request ID: {request_id}\n"
                f"OpenAI hop result: {openai_status}\n"
                f"OpenAI message: {openai_reply[:300] or 'NO_REPLY'}\n\n"
                "Reply with GEMINI_CHANNEL_OK on the first line, followed by one short "
                "sentence confirming that you received this test message."
            ),
        )
        gemini_status = "PASS" if "GEMINI_CHANNEL_OK" in gemini_reply else "FAIL"
        if gemini_status != "PASS":
            errors.append("GEMINI=UNEXPECTED_REPLY")
    except Exception as exc:
        errors.append(f"GEMINI={safe_error(exc)}")

if openai_key and openai_status == "PASS" and gemini_status == "PASS":
    try:
        verify_reply = openai_text(
            openai_client,
            (
                "Verify this private AI-channel test result. "
                f"Request ID: {request_id}. "
                f"Gemini reply: {gemini_reply[:600]}. "
                "If the Gemini reply contains GEMINI_CHANNEL_OK, reply exactly PASS. "
                "Otherwise reply exactly FAIL."
            ),
        )
        verify_status = "PASS" if verify_reply.strip().upper().startswith("PASS") else "FAIL"
        if verify_status != "PASS":
            errors.append("OPENAI_VERIFY=UNEXPECTED_REPLY")
    except Exception as exc:
        errors.append(f"OPENAI_VERIFY={safe_error(exc)}")
else:
    errors.append("OPENAI_VERIFY=SKIPPED_PREREQUISITE")

pre_discord_overall = (
    "PASS"
    if openai_status == "PASS"
    and gemini_status == "PASS"
    and verify_status == "PASS"
    else "FAIL"
)

report = (
    f"**CODEBLACK AI CHANNEL TEST**\n"
    f"Request ID: `{request_id}`\n"
    f"Time: {now.isoformat()}\n"
    f"OpenAI ({OPENAI_MODEL}): **{openai_status}**\n"
    f"Gemini Pro ({GEMINI_MODEL}): **{gemini_status}**\n"
    f"OpenAI verification: **{verify_status}**\n"
    f"Pre-Discord overall: **{pre_discord_overall}**\n"
)

if errors:
    report += "Diagnostics: `" + "; ".join(errors)[:700] + "`\n"

if discord_hook:
    try:
        sep = "&" if "?" in discord_hook else "?"
        response = requests.post(
            f"{discord_hook}{sep}wait=true",
            json={"content": report[:1900]},
            timeout=20,
        )
        if 200 <= response.status_code < 300:
            discord_status = "PASS"
        else:
            errors.append(f"DISCORD=HTTP_{response.status_code}")
    except Exception as exc:
        errors.append(f"DISCORD={type(exc).__name__}")
else:
    errors.append("DISCORD=MISSING_SECRET")

overall = (
    "PASS"
    if pre_discord_overall == "PASS" and discord_status == "PASS"
    else "FAIL"
)

print(f"REQUEST_ID={request_id}")
print(f"OPENAI_STATUS={openai_status}")
print(f"GEMINI_STATUS={gemini_status}")
print(f"OPENAI_VERIFY_STATUS={verify_status}")
print(f"DISCORD_STATUS={discord_status}")
print(f"OVERALL={overall}")
if errors:
    print("DIAGNOSTICS=" + "; ".join(errors))

sys.exit(0 if overall == "PASS" else 1)
