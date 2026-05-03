from __future__ import annotations
import json


def parse_string_list(response: str) -> list[str]:
    """从 LLM 响应中解析字符串列表。先尝试 JSON 数组，失败则按行分割。"""
    text = response.strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item]
    except (json.JSONDecodeError, ValueError):
        pass
    return [line.strip() for line in text.splitlines() if line.strip()]


def parse_object(response: str) -> dict:
    """从 LLM 响应中解析 JSON 对象。失败返回空 dict，不抛异常。"""
    text = response.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return {}
