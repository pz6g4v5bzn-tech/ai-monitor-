import os
from openai import OpenAI
import requests

# 1. Credentials from your GitHub Secrets
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
DISCORD_HOOK = os.environ.get("DISCORD_HOOK")
TARGET_GITHUB_TOKEN = os.environ.get("TARGET_GITHUB_TOKEN")
TARGET_REPO = os.environ.get("TARGET_REPO", "pz6g4v5bzn-tech/evidence-desk-lab")

openai_client = OpenAI(api_key=OPENAI_KEY)
gemini_client = OpenAI(
    api_key=GEMINI_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)


def get_repo_telemetry(repo: str, token: str) -> str:
    """Fetches recent commits, issues, and actions from the monitored repo."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    telemetry = []

    # Commits
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo}/commits?per_page=3",
            headers=headers,
            timeout=10,
        )
        if r.status_code == 200:
            commits = [
                f"- {c['commit']['message'].splitlines()[0]} (by {c['commit']['author']['name']})"
                for c in r.json()
            ]
            telemetry.append("Recent Commits:\n" + "\n".join(commits))
    except Exception as e:
        telemetry.append(f"Commits error: {e}")

    # Issues
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo}/issues?state=open&per_page=3",
            headers=headers,
            timeout=10,
        )
        if r.status_code == 200:
            issues = [f"- #{i['number']}: {i['title']}" for i in r.json()]
            telemetry.append(
                "Open Issues/PRs:\n"
                + ("\n".join(issues) if issues else "None open.")
            )
    except Exception as e:
        telemetry.append(f"Issues error: {e}")

    # Actions
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo}/actions/runs?per_page=2",
            headers=headers,
            timeout=10,
        )
        if r.status_code == 200:
            runs = [
                f"- {run['name']}: {run['status']} ({run['conclusion'] or 'running'})"
                for run in r.json().get("workflow_runs", [])
            ]
            telemetry.append(
                "Workflows:\n"
                + ("\n".join(runs) if runs else "No recent workflow runs.")
            )
    except Exception as e:
        telemetry.append(f"Actions error: {e}")

    return "\n\n".join(telemetry) if telemetry else "No telemetry found."


def query_model(client, model: str, system_prompt: str, prompt: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


telemetry_data = get_repo_telemetry(TARGET_REPO, TARGET_GITHUB_TOKEN)

gemini_prompt = f"""Live telemetry from target repo '{TARGET_REPO}':
{telemetry_data}

Conduct an hourly technical audit:
1. Is the project making progress or stalling based on commits?
2. Are any runner workflows failing?
3. What is the immediate priority?"""

GEMINI_SYSTEM = (
    "You are a technical code supervisor. Be ultra-concise, max 3 bullet points."
)
CHATGPT_SYSTEM = "You are the project lead orchestrator. Respond with concrete actions and fixes. Max 3 bullet points."

gemini_question = query_model(
    client=gemini_client,
    model="gemini-3.6-flash",
    system_prompt=GEMINI_SYSTEM,
    prompt=gemini_prompt,
)

chatgpt_status = query_model(
    client=openai_client,
    model="gpt-4o-mini",
    system_prompt=CHATGPT_SYSTEM,
    prompt=f"Telemetry:\n{telemetry_data}\n\nSupervisor question:\n{gemini_question}",
)

gemini_directive = query_model(
    client=gemini_client,
    model="gemini-3.6-flash",
    system_prompt=GEMINI_SYSTEM,
    prompt=f"ChatGPT stated: '{chatgpt_status}'. Give one final operational command.",
)

report = (
    f"**[HOURLY AUDIT: {TARGET_REPO}]**\n\n"
    f"📊 **Telemetry:**\n```{telemetry_data[:300]}```\n\n"
    f"🔍 **Gemini Inspector:**\n{gemini_question}\n\n"
    f"🤖 **ChatGPT Action Plan:**\n{chatgpt_status}\n\n"
    f"📌 **Gemini Directive:**\n{gemini_directive}"
)

if DISCORD_HOOK:
    requests.post(DISCORD_HOOK, json={"content": report[:1950]})
