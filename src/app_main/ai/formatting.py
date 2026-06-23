from __future__ import annotations

import re

import markdown


_MARKDOWN_EXTENSIONS = ("extra", "nl2br", "sane_lists")


def ai_summary_to_html(text: str) -> str:
    """将 AI 总结的 Markdown 转为可嵌入邮件的 HTML 片段。"""
    return markdown.markdown(
        text,
        extensions=_MARKDOWN_EXTENSIONS,
        output_format="html5",
    )


def ai_summary_to_plain(text: str) -> str:
    """将 Markdown 总结转为纯文本，供 text/plain 邮件使用。"""
    html = ai_summary_to_html(text)
    plain = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    plain = re.sub(r"</(p|li|h[1-6])>", "\n", plain, flags=re.IGNORECASE)
    plain = re.sub(r"<[^>]+>", "", plain)
    plain = re.sub(r"\n{3,}", "\n\n", plain)
    return plain.strip()
