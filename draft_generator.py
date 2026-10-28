import json
import os
import re
from typing import Optional

from openai import OpenAI


SYSTEM_PROMPT = """You are a compliance-first creator outreach consultant.
Generate exactly 3 versions of an English outreach draft (formal, friendly, short) based on the client brief and candidate info.

Rules:
- Do NOT bulk-message or auto-send. Drafts are for manual review and manual sending only.
- The first sentence must be personalized and reference the candidate's specific content or style.
- Clearly state the collaboration format, compensation range, and timeline.
- Include an opt-out line (e.g., "If this isn't a fit, just let me know and I won't follow up.").
- Output ONLY valid JSON with this exact schema:
{"drafts":[{"style":"formal","subject":"...","body":"..."},{"style":"friendly","subject":"...","body":"..."},{"style":"short","subject":"...","body":"..."}]}
"""


def _extract_json(raw: str) -> Optional[dict]:
    """Best-effort JSON extraction from LLM output."""
    if not raw:
        return None

    raw = raw.strip()

    # Remove markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        raw = raw.strip()

    # Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fallback: find the first {...} block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    return None


def generate_outreach_drafts(
    brief: dict,
    candidate: dict,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> list[dict]:
    """
    Generate 3 English outreach drafts (formal / friendly / short).

    Returns a list of dicts: [{"style": ..., "subject": ..., "body": ...}, ...]
    Returns an empty list if API key is missing or generation fails.
    """
    key = (api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
    if not key:
        print("[draft_generator] No OpenAI API key provided.")
        return []

    client = OpenAI(api_key=key)

    user_prompt = f"""Client Brief:
- Product / Service: {brief.get('product', '')}
- Target Market: {brief.get('target_market', '')}
- Campaign Goal: {brief.get('goal', '')}
- Budget: {brief.get('budget_text', '')}

Candidate Info:
- Name: {candidate.get('name', '')}
- Platform: {candidate.get('platform', '')}
- Followers: {candidate.get('followers', 0)}
- Content Summary: {candidate.get('content_summary', '')}
- Estimated Price: {candidate.get('estimated_price', 0)}

Generate exactly 3 English outreach drafts (formal, friendly, short) in the required JSON schema.
"""

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        print(f"[draft_generator] OpenAI API error: {e}")
        return []

    raw = resp.choices[0].message.content if resp.choices else ""
    data = _extract_json(raw)

    if not data:
        print(f"[draft_generator] Failed to parse JSON. Raw output (first 500 chars): {raw[:500]}")
        return []

    drafts = data.get("drafts", [])
    if not isinstance(drafts, list) or not drafts:
        print("[draft_generator] No drafts in parsed JSON.")
        return []

    # Basic validation and normalization
    cleaned: list[dict] = []
    for d in drafts:
        if isinstance(d, dict) and d.get("body"):
            cleaned.append({
                "style": d.get("style", "unknown"),
                "subject": d.get("subject", ""),
                "body": d.get("body", ""),
            })

    return cleaned
