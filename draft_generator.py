import json
from openai import OpenAI


SYSTEM_PROMPT = """你是一位合规的创作者拓展顾问。
请根据客户需求，生成 3 个版本的英文联系草稿（正式、亲切、短版）。
要求：
- 不群发、不自动发送，草稿仅供人工审核后手动发送。
- 第一句必须个性化，提及对方的具体内容或风格。
- 明确说明合作形式、报酬范围、时间预期。
- 包含退出机制（如“If this isn't a fit, just let me know and I won't follow up.”）。
只输出 JSON，格式：
{"drafts":[{"style":"formal","subject":"...","body":"..."},{"style":"friendly","subject":"...","body":"..."},{"style":"short","subject":"...","body":"..."}]}
"""


def generate_outreach_drafts(brief: dict, candidate: dict) -> list[dict]:
    client = OpenAI()

    user_prompt = f"""
客户 Brief：
- 产品/服务：{brief.get('product', '')}
- 目标市场：{brief.get('target_market', '')}
- 合作目标：{brief.get('goal', '')}
- 预算：{brief.get('budget_text', '')}

候选人信息：
- 名称：{candidate.get('name', '')}
- 平台：{candidate.get('platform', '')}
- 粉丝数：{candidate.get('followers', 0)}
- 内容摘要：{candidate.get('content_summary', '')}
- 预估报价：{candidate.get('estimated_price', 0)}

请生成 3 个版本的英文联系草稿。
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        data = json.loads(raw)
        return data.get("drafts", [])
    except json.JSONDecodeError:
        return []
