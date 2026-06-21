"""Deterministic HTML node serializer for component renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from typing import Any, Iterable


Child = "HtmlNode | str"


@dataclass(frozen=True)
class HtmlNode:
    tag: str
    attrs: dict[str, Any] = field(default_factory=dict)
    children: tuple[Child, ...] = ()


VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def h(tag: str, attrs: dict[str, Any] | None = None, children: Iterable[Child] | Child | None = None) -> HtmlNode:
    if children is None:
        clean_children: tuple[Child, ...] = ()
    elif isinstance(children, (HtmlNode, str)):
        clean_children = (children,)
    else:
        clean_children = tuple(child for child in children if child is not None)
    return HtmlNode(tag=tag, attrs=attrs or {}, children=clean_children)


def render_node(node: Child) -> str:
    if isinstance(node, str):
        return escape(node, quote=False)
    attrs = _render_attrs(node.attrs)
    if node.tag in VOID_TAGS and not node.children:
        return f"<{node.tag}{attrs}>"
    if node.tag == "style":
        children = "".join(str(child) for child in node.children)
    else:
        children = "".join(render_node(child) for child in node.children)
    return f"<{node.tag}{attrs}>{children}</{node.tag}>"


def render_document(head_children: list[HtmlNode], body_children: list[HtmlNode]) -> str:
    document = h(
        "html",
        {"lang": "zh-Hans"},
        [
            h("head", children=head_children),
            h("body", children=body_children),
        ],
    )
    return "<!doctype html>\n" + render_node(document)


def _render_attrs(attrs: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in sorted(attrs):
        value = attrs[key]
        if value is False or value is None:
            continue
        if value is True:
            parts.append(escape(str(key), quote=True))
            continue
        parts.append(f'{escape(str(key), quote=True)}="{escape(str(value), quote=True)}"')
    return (" " + " ".join(parts)) if parts else ""
