from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

import llm_config
import prompts
from case_utils import parse_patient_scenario

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
DEEPSEEK_BASE_URL = (
    os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.deepseek.com"
)
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL") or os.getenv("OPENAI_MODEL") or "deepseek-v4-flash"


def llm_mode_info() -> dict:
    """返回当前 LLM 运行模式（供 /api/health 与管理页确认是否已联通大模型）。"""
    if os.getenv("LLM_MOCK") == "1":
        return {
            "mode": "mock",
            "reason": "LLM_MOCK=1 强制走内置 Mock（仅端到端测试使用）",
            "model": None,
            "base_url": None,
        }
    config = llm_config.get_active_llm_config()
    if config and config.get("baseUrl"):
        return {
            "mode": "real",
            "reason": "llm_configs 表配置优先",
            "model": config.get("model") or DEEPSEEK_MODEL,
            "base_url": config["baseUrl"],
        }
    if DEEPSEEK_API_KEY:
        return {
            "mode": "real",
            "reason": "backend/.env 注入的 DEEPSEEK_API_KEY",
            "model": DEEPSEEK_MODEL,
            "base_url": DEEPSEEK_BASE_URL,
        }
    return {
        "mode": "mock",
        "reason": "未配置任何 LLM（无 DEEPSEEK_API_KEY / llm_configs）",
        "model": None,
        "base_url": None,
    }


def _chat_completion(messages: list[dict[str, str]], temperature: float = 0.3) -> str | None:
    # LLM_MOCK=1 强制走内置 Mock（供确定性的端到端测试；真实训练环境不要设置）。
    if os.getenv("LLM_MOCK") == "1":
        return None

    config = llm_config.get_active_llm_config()

    if config and config.get("baseUrl"):
        base_url = config["baseUrl"]
        model = config.get("model") or DEEPSEEK_MODEL
        headers = llm_config.build_headers(config)
    else:
        if not DEEPSEEK_API_KEY:
            return None
        base_url = DEEPSEEK_BASE_URL
        model = DEEPSEEK_MODEL
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}

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

    # Mock 降级：按「概括病史 → 诊断 → 鉴别 → 体格检查 → 辅助检查 → 处理」顺序推进，
    # 并在「体格检查」「辅助检查」小节结束后输出 [PART: pe] / [PART: investigations] 分节标记
    # （供前端解密对应的结果卡片）。
    count = len([m for m in messages if m.get("role") == "user"])
    if count == 0:
        return "Please summarise the patient's medical history in one minute."
    if count == 1:
        return "Thank you. What do you consider the most likely diagnosis, and on what evidence?"
    if count == 2:
        return "What are your differential diagnoses, and how would you distinguish between them?"
    if count == 3:
        return "What physical examination would you perform, and what findings would you expect in this case?"
    if count == 4:
        return (
            "Your physical-examination approach is reasonable.\n\n"
            "[PART: pe]\n\n"
            "Now, what investigations would you order, and what results do you expect?"
        )
    if count == 5:
        return (
            "Your investigation plan is appropriate.\n\n"
            "[PART: investigations]\n\n"
            "What is your management plan, red flags, and referral criteria?"
        )
    if count == 6:
        return "Please summarise your overall management and follow-up plan in one or two sentences."
    return "Thank you. When you are ready, please submit your review."


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
