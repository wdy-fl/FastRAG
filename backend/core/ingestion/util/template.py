from __future__ import annotations
import re

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def render_template(template: str | None, **kwargs: object) -> str:
    """渲染 {{variable}} 模板。template 为 None 时返回 kwargs['text'] 或空串。"""
    if template is None:
        return str(kwargs.get("text", ""))

    def replace(m: re.Match) -> str:
        key = m.group(1)
        return str(kwargs[key]) if key in kwargs else m.group(0)

    return _VAR_RE.sub(replace, template)
