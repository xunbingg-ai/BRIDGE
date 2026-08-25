from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

import llm_config
import prompts
from case_utils import parse_patient_scenario

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
        [{"role": "system", "content": prompts.patient_system_prompt(case)}, *messages],
        temperature=0.5,
    )
    if ai_reply:
        return ai_reply

    # Mock 降级：绝不回吐完整病人剧本 / summary。只按学生问到的内容给简短、患者口吻的回答。
    last_text = messages[-1]["content"] if messages else ""
    facts = parse_patient_scenario(case.get("patient_scenario") or "")
    complaint = facts["complaint"].rstrip("。，,. ")
    duration = facts["duration"].rstrip("。，,. ")

    if any(word in last_text for word in ["哪里不舒服", "怎么不舒服", "什么症状", "哪里疼", "怎么了", "症状", "哪里不"]):
        if complaint:
            return f"我最近就是{complaint}，一直不太舒服，您帮我看看到底是怎么回事吧。"
        return "我最近感觉不太舒服，您给我看看是哪里出了问题。"

    if any(word in last_text for word in ["多久", "几天", "多长时间", "什么时候开始", "几天了", "什么时候"]):
        if duration:
            return f"大概有{duration}了，这几天都没怎么好转。"
        return "大概有几天了吧，具体多少我也记不太清，反正一直不好。"

    if any(word in last_text for word in ["多大", "年龄", "几岁", "男的女的", "性别", "多大了"]):
        if facts["age"]:
            return f"我{facts['age']}岁。"
        return "哦，我也不算年轻了。"

    return "嗯，是的。具体我也说不太清楚，就是感觉不太舒服。您还想了解哪方面的情况呢？"


def examiner_reply(case: dict[str, Any], messages: list[dict[str, str]]) -> str:
    ai_reply = _chat_completion(
        [{"role": "system", "content": prompts.examiner_system_prompt(case)}, *messages],
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


def _build_transcript(content: dict[str, Any]) -> str:
    """把会话内容扁平化为可读的对话文本，供评估 prompt 内联使用。"""
    lines: list[str] = []
    for phase in ("patient_phase", "examiner_phase"):
        for m in content.get(phase, []) or []:
            role = m.get("role") or "user"
            text = (m.get("content") or "").strip()
            if role in {"user", "assistant"} and text:
                label = "Student" if role == "user" else (
                    "Examiner" if phase == "examiner_phase" else "Patient"
                )
                lines.append(f"{label}: {text}")
    return "\n\n".join(lines)


def grade_session(case: dict[str, Any], content: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    transcript = _build_transcript(content)
    system_prompt = prompts.assessment_system_prompt(case, transcript)

    ai_reply = _chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "Please provide the assessment now. Reply with ONLY the JSON object.",
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
