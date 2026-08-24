from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

import llm_config

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _chat_completion(messages: list[dict[str, str]], temperature: float = 0.3) -> str | None:
    config = llm_config.get_active_llm_config()

    if config and config.get("baseUrl"):
        base_url = config["baseUrl"]
        model = config.get("model") or OPENAI_MODEL
        headers = llm_config.build_headers(config)
    else:
        if not OPENAI_API_KEY:
            return None
        base_url = OPENAI_BASE_URL
        model = OPENAI_MODEL
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    if not base_url or not model or not headers:
        return None

    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers=headers,
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
        },
        timeout=90,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def patient_reply(case: dict[str, Any], messages: list[dict[str, str]]) -> str:
    ai_reply = _chat_completion(
        [{"role": "system", "content": case["patient_prompt"]}, *messages],
        temperature=0.5,
    )
    if ai_reply:
        return ai_reply

    last_text = messages[-1]["content"] if messages else ""
    summary = case.get("summary") or "我最近身体有些不适。"
    if len(messages) <= 1:
        return f"医生您好，我最近确实不舒服。简单说就是：{summary}"
    if any(word in last_text for word in ["多久", "什么时候", "几天"]):
        return "大概有几天了，感觉比刚开始更明显一些。"
    if any(word in last_text for word in ["哪里", "部位", "怎么"]):
        return f"主要是和您刚才问的差不多，我再说具体一点：{summary}"
    return "嗯，是的。我最近作息也不算好，症状有时候会加重，尤其是活动或者劳累之后。"


def examiner_reply(case: dict[str, Any], messages: list[dict[str, str]]) -> str:
    ai_reply = _chat_completion(
        [{"role": "system", "content": case["examiner_prompt"]}, *messages],
        temperature=0.4,
    )
    if ai_reply:
        return ai_reply

    count = len([m for m in messages if m.get("role") == "user"])
    if count == 0:
        return "第一阶段问诊已结束。请先给出你的初步诊断和主要诊断依据。"
    if count == 1:
        return "请补充你的鉴别诊断，以及下一步需要完善的辅助检查。"
    if count == 2:
        return "请简述治疗原则、转诊指征和需要向患者交代的注意事项。"
    return "好的，请结合刚才的信息，用一两句话总结你的诊疗计划。"


def _extract_json(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _fallback_grade(content: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    patient_messages = content.get("patient_phase", []) or []
    examiner_messages = content.get("examiner_phase", []) or []
    patient_user_count = sum(1 for m in patient_messages if m.get("role") == "user")
    examiner_user_count = sum(1 for m in examiner_messages if m.get("role") == "user")

    history_taking = min(30, 18 + patient_user_count * 2)
    communication = min(25, 15 + patient_user_count)
    clinical_reasoning = min(25, 12 + examiner_user_count * 3)
    professionalism = 18
    total_score = round(history_taking + communication + clinical_reasoning + professionalism, 1)

    score = {
        "total_score": total_score,
        "max_score": 100,
        "sub_scores": {
            "history_taking": history_taking,
            "communication": communication,
            "clinical_reasoning": clinical_reasoning,
            "professionalism": professionalism,
        },
        "graded_at": _now_for_grade(),
    }

    report = {
        "summary": "本次练习已完成。系统当前使用演示评分规则；接入 OPENAI_API_KEY 或在管理员页配置模型后可由大模型生成更精细的个性化评语。",
        "strengths": ["完成了病史采集阶段", "能够进入考官问答阶段并表达诊疗思路"],
        "weaknesses": ["建议进一步追问既往史、过敏史和用药史", "鉴别诊断可更系统化"],
        "suggestions": ["按 OLDCART 系统问诊", "提交前留出时间总结诊疗计划"],
        "detailed_comments": [
            {
                "criteria": "病史采集",
                "score": history_taking,
                "max_score": 30,
                "comment": "已覆盖主诉和基本现病史，建议补充既往史与系统回顾。",
            },
            {
                "criteria": "沟通技巧",
                "score": communication,
                "max_score": 25,
                "comment": "沟通结构基本清楚，可增加共情表达和开放式提问。",
            },
            {
                "criteria": "临床推理",
                "score": clinical_reasoning,
                "max_score": 25,
                "comment": "能形成初步判断，建议继续强化鉴别诊断与辅助检查选择。",
            },
            {
                "criteria": "职业素养",
                "score": professionalism,
                "max_score": 20,
                "comment": "能够围绕病例展开，后续可更自然地进行风险沟通。",
            },
        ],
    }
    return score, report


def _now_for_grade() -> str:
    from datetime import datetime

    return datetime.now().astimezone().isoformat(timespec="seconds")


def grade_session(case: dict[str, Any], content: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    prompt = (
        "你是OSCE考官，请根据病例、参考答案和考生完整对话进行评分。"
        "只返回一个JSON对象，不要包含Markdown代码块。格式如下："
        '{"total_score": 82.5, "max_score": 100, '
        '"sub_scores": {"history_taking": 25, "communication": 22, '
        '"clinical_reasoning": 20, "professionalism": 15.5}, '
        '"summary": "总体评价", "strengths": ["优点"], '
        '"weaknesses": ["不足"], "suggestions": ["建议"], '
        '"detailed_comments": [{"criteria": "病史采集", "score": 25, '
        '"max_score": 30, "comment": "具体评价"}]}'
    )

    ai_reply = _chat_completion(
        [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "case_title": case.get("title"),
                        "reference_answer": case.get("reference_answer"),
                        "conversation": content,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        temperature=0.1,
    )

    if ai_reply:
        parsed = _extract_json(ai_reply)
        if parsed:
            try:
                score = {
                    "total_score": float(parsed.get("total_score", 0)),
                    "max_score": float(parsed.get("max_score", 100)),
                    "sub_scores": parsed.get("sub_scores", {}),
                    "graded_at": _now_for_grade(),
                }
                report = {
                    "summary": parsed.get("summary", ""),
                    "strengths": parsed.get("strengths", []),
                    "weaknesses": parsed.get("weaknesses", []),
                    "suggestions": parsed.get("suggestions", []),
                    "detailed_comments": parsed.get("detailed_comments", []),
                }
                return score, report
            except (TypeError, ValueError):
                pass

    return _fallback_grade(content)
