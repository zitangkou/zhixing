"""清洗运营产出的时评精拆 HTML，保留版式结构；去掉脚本与事件。"""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser

_SKIP = {"script", "iframe", "object", "embed", "link", "meta", "svg", "noscript", "form", "input", "button"}
_ALLOW = {
    "div", "p", "span", "b", "strong", "i", "em", "br", "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "ul", "ol", "li", "a", "pre",
    "blockquote", "hr", "section", "article",
}
_VOID = {"br", "hr"}
_ATTR = {"style", "href", "colspan", "rowspan", "align", "class"}
_MAX_CHARS = 200_000
_STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.I | re.S)


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in _SKIP or tag == "style":
            self._skip += 1
            return
        if self._skip or tag not in _ALLOW:
            return
        attr_html = self._fmt(attrs)
        if tag in _VOID:
            self.parts.append(f"<{tag}{attr_html} />")
        else:
            self.parts.append(f"<{tag}{attr_html}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP or tag == "style":
            self._skip = max(0, self._skip - 1)
            return
        if self._skip or tag not in _ALLOW or tag in _VOID:
            return
        self.parts.append(f"</{tag}>")

    def handle_startendtag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in _SKIP or tag == "style" or self._skip or tag not in _ALLOW:
            return
        attr_html = self._fmt(attrs)
        if tag in _VOID:
            self.parts.append(f"<{tag}{attr_html} />")
        else:
            self.parts.append(f"<{tag}{attr_html}></{tag}>")

    def handle_data(self, data: str) -> None:
        if self._skip or not data:
            return
        self.parts.append(escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if not self._skip:
            self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self._skip:
            self.parts.append(f"&#{name};")

    def _fmt(self, attrs) -> str:
        bits = []
        for key, val in attrs:
            key = key.lower()
            if key.startswith("on") or key.startswith("data-"):
                continue
            if key not in _ATTR or val is None:
                continue
            if key == "href":
                href = val.strip()
                if not re.match(r"^https?://", href, re.I):
                    continue
                bits.append(f'href="{escape(href, quote=True)}"')
                continue
            bits.append(f'{key}="{escape(val, quote=True)}"')
        return (" " + " ".join(bits)) if bits else ""


def _safe_css(css: str) -> str:
    text = css or ""
    text = re.sub(r"@import[^;]+;", "", text, flags=re.I)
    text = re.sub(r"expression\s*\(", "", text, flags=re.I)
    text = re.sub(r"javascript\s*:", "", text, flags=re.I)
    text = re.sub(r"url\s*\(\s*['\"]?\s*javascript", "", text, flags=re.I)
    text = re.sub(r"\bbody\s*\{", "html,body{", text, flags=re.I)
    return text.strip()


def _extract_css(raw: str) -> str:
    chunks = [_safe_css(m.group(1)) for m in _STYLE_RE.finditer(raw or "")]
    return "\n".join(c for c in chunks if c)


def sanitize_display_html(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    if len(text) > _MAX_CHARS:
        raise ValueError("HTML 过长，请只贴正文（去掉长图）")
    css = _extract_css(text)
    lower = text.lower()
    start = lower.find("<body")
    if start >= 0:
        gt = text.find(">", start)
        end = lower.rfind("</body>")
        text = text[gt + 1 : end] if end > gt else text[gt + 1 :]
    parser = _Sanitizer()
    parser.feed(text)
    parser.close()
    inner = "".join(parser.parts).strip()
    if not inner:
        return ""
    style = f"<style>{css}</style>" if css else ""
    return f"{style}{inner}"
