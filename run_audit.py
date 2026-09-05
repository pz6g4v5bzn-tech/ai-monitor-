import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from openai import OpenAI

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-sol").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash").strip()
TARGET_REPO = os.environ.get(
    "TARGET_REPO", "pz6g4v5bzn-tech/evidence-desk-lab"
).strip()


def clean_secret(name: str) -> str:
    """Normalize a GitHub Actions secret without ever printing it."""
    value = os.environ.get(name, "")
    value = value.replace("\r", "").replace("\n", "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def safe_error(exc: Exception) -> str:
    """Return a secret-safe error classification for logs and Discord."""
    status = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)
    parts = [type(exc).__name__]
    if status is not None:
        parts.append(f"status={status}")
    if code:
        parts.append(f"code={code}")
    return " ".join(parts)


def get_repo_telemetry(repo: str, token: str) -> str:
    """Fetch recent commits, open issues/PRs, and workflow runs."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "codeblack-ai-monitor",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    telemetry = []

    def get_json(path: str):
        response = requests.get(
            f"https://api.github.com/repos/{repo}/{path}",
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    try:
        commits_json = get_json("commits?per_page=3")
        commits = [
            f"- {item['commit']['message'].splitlines()[0]} "
            f"(by {item['commit']['author']['name']})"
            for item in commits_json
        ]
        telemetry.append(
            "Recent Commits:\n" + ("\n".join(commits) if commits else "None.")
        )
    except Exception as exc:
        telemetry.append(f"Commits telemetry: ERROR {safe_error(exc)}")

    try:
        issues_json = get_json("issues?state=open&per_page=3")
        issues = [f"- #{item['number']}: {item['title']}" for item in issues_json]
        telemetry.append(
            "Open Issues/PRs:\n" + ("\n".join(issues) if issues else "None open.")
        )
    except Exception as exc:
        telemetry.append(f"Issues telemetry: ERROR {safe_error(exc)}")

    try:
        actions_json = get_json("actions/runs?per_page=3")
        runs = [
            f"- {run['name']}: {run['status']} ({run['conclusion'] or 'running'})"
            for run in actions_json.get("workflow_runs", [])
        ]
        telemetry.append(
            "Workflows:\n" + ("\n".join(runs) if runs else "No recent runs.")
        )
    except Exception as exc:
        telemetry.append(f"Actions telemetry: ERROR {safe_error(exc)}")

    return "\n\n".join(telemetry)


def query_openai(client: OpenAI, system_prompt: str, prompt: str) -> str:
    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=system_prompt,
        input=prompt,
        max_output_tokens=300,
    )
    return (response.output_text or "").strip()


def query_gemini(client: OpenAI, system_prompt: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=GEMINI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=300,
    )
    return (response.choices[0].message.content or "").strip()


GEMINI_SYSTEM = """You are an automated technical project supervisor.
Audit the current repository state, runners, bugs, stalls, and progress against the blueprint.
Rules:
- Be extremely brief, sharp, and direct.
- Ask or state only what is supported by the supplied telemetry.
- Never exceed 3 bullet points.
- Never claim live VM/host facts that are not present in the telemetry."""

CHATGPT_SYSTEM = """You are an AI system orchestrator and project lead.
Report only what the supplied repository telemetry and Gemini inspection support.
Rules:
- Use ultra-concise status: State (OK/Stall/Error), progress, blockers, immediate action.
- Be strictly factual.
- Never invent VM, runner, supervisor, or completion evidence.
- Never exceed 3 bullet points."""

now = datetime.now(ZoneInfo("America/New_York"))
request_id = f"CB-HOURLY-{now.strftime('%Y%m%d-%H%M%S')}"

openai_key = clean_secret("OPENAI_API_KEY")
gemini_key = clean_secret("GEMINI_API_KEY")
discord_hook = clean_secret("DISCORD_HOOK")
github_token = clean_secret("TARGET_GITHUB_TOKEN")

telemetry_data = get_repo_telemetry(TARGET_REPO, github_token)

gemini_status = "FAIL"
openai_status = "FAIL"
gemini_directive_status = "SKIPPED"
discord_status = "FAIL"

gemini_question = ""
chatgpt_status = ""
gemini_directive = ""
errors = []

initial_audit = f"""Hourly Project Audit for {TARGET_REPO}.

Telemetry:
{telemetry_data}

Assess:
1. Is the project advancing or stalled?
2. What completed or changed recently?
3. Any workflow/runner/API failures visible?
4. What needs immediate attention?"""

if not gemini_key:
    errors.append("GEMINI=MISSING_SECRET")
else:
    try:
        gemini_client = OpenAI(
            api_key=gemini_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        gemini_question = query_gemini(
            gemini_client,
            GEMINI_SYSTEM,
            initial_audit,
        )
        if gemini_question:
            gemini_status = "PASS"
        else:
            errors.append("GEMINI=EMPTY_RESPONSE")
    except Exception as exc:
        errors.append(f"GEMINI={safe_error(exc)}")

if not openai_key:
    errors.append("OPENAI=MISSING_SECRET")
else:
    try:
        openai_client = OpenAI(api_key=openai_key)
        chatgpt_status = query_openai(
            openai_client,
            CHATGPT_SYSTEM,
            (
                f"Repository telemetry:\n{telemetry_data}\n\n"
                f"Gemini inspector status: {gemini_status}\n"
                f"Gemini inspector output:\n"
                f"{gemini_question or 'No Gemini response available.'}\n\n"
                "Give the factual project-lead status and immediate next action."
            ),
        )
        if chatgpt_status:
            openai_status = "PASS"
        else:
            errors.append("OPENAI=EMPTY_RESPONSE")
    except Exception as exc:
        errors.append(f"OPENAI={safe_error(exc)}")

if gemini_status == "PASS" and openai_status == "PASS":
    try:
        gemini_directive = query_gemini(
            gemini_client,
            GEMINI_SYSTEM,
            (
                f"ChatGPT reported:\n{chatgpt_status}\n\n"
                "Give one final concise operational directive based only on the telemetry."
            ),
        )
        if gemini_directive:
            gemini_directive_status = "PASS"
        else:
            gemini_directive_status = "FAIL"
            errors.append("GEMINI_DIRECTIVE=EMPTY_RESPONSE")
    except Exception as exc:
        gemini_directive_status = "FAIL"
        errors.append(f"GEMINI_DIRECTIVE={safe_error(exc)}")
else:
    errors.append("GEMINI_DIRECTIVE=SKIPPED_PREREQUISITE")

ai_path_status = (
    "PASS"
    if gemini_status == "PASS"
    and openai_status == "PASS"
    and gemini_directive_status == "PASS"
    else "FAIL"
)

report = (
    f"**CODEBLACK HOURLY AI AUDIT**\n"
    f"Request ID: `{request_id}`\n"
    f"Time: {now.isoformat()}\n"
    f"Target: `{TARGET_REPO}`\n"
    f"OpenAI ({OPENAI_MODEL}): **{openai_status}**\n"
    f"Gemini ({GEMINI_MODEL}): **{gemini_status}**\n"
    f"Gemini final directive: **{gemini_directive_status}**\n"
    f"AI path: **{ai_path_status}**\n\n"
)

if gemini_question:
    report += f"**Gemini Inspector**\n{gemini_question[:450]}\n\n"
if chatgpt_status:
    report += f"**ChatGPT Action Plan**\n{chatgpt_status[:450]}\n\n"
if gemini_directive:
    report += f"**Gemini Directive**\n{gemini_directive[:300]}\n\n"
if errors:
    report += "Diagnostics: `" + "; ".join(errors)[:500] + "`\n"

if not discord_hook:
    errors.append("DISCORD=MISSING_SECRET")
else:
    try:
        separator = "&" if "?" in discord_hook else "?"
        response = requests.post(
            f"{discord_hook}{separator}wait=true",
            json={"content": report[:1950]},
            timeout=20,
        )
        if 200 <= response.status_code < 300:
            discord_status = "PASS"
        else:
            errors.append(f"DISCORD=HTTP_{response.status_code}")
    except Exception as exc:
        errors.append(f"DISCORD={safe_error(exc)}")

overall = "PASS" if ai_path_status == "PASS" and discord_status == "PASS" else "FAIL"

print(f"REQUEST_ID={request_id}")
print(f"TARGET_REPO={TARGET_REPO}")
print(f"OPENAI_MODEL={OPENAI_MODEL}")
print(f"GEMINI_MODEL={GEMINI_MODEL}")
print(f"OPENAI_STATUS={openai_status}")
print(f"GEMINI_STATUS={gemini_status}")
print(f"GEMINI_DIRECTIVE_STATUS={gemini_directive_status}")
print(f"DISCORD_STATUS={discord_status}")
print(f"OVERALL={overall}")
if errors:
    print("DIAGNOSTICS=" + "; ".join(errors))

sys.exit(0 if overall == "PASS" else 1)
