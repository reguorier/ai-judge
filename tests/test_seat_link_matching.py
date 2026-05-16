from __future__ import annotations

from types import SimpleNamespace

from bridges.chrome_cdp_bridge import CDPTab, _match_tab as match_cdp_tab
from bridges.chrome_fixed_tab_bridge import ChromeTab, _match_tab as match_fixed_tab
from bridges.web_seat_bridge import _fixed_chrome_tab_available


def test_fixed_tab_matches_old_conversation_by_stable_domain():
    config = {
        "url": "https://grok.com/",
        "fresh_url": "https://grok.com/",
        "match_domains": ["grok.com"],
        "browser_label": "Grok / grok.com",
        "provider": "Grok",
    }
    tab = ChromeTab(
        window_index=1,
        tab_index=4,
        title="AI Judge Python CLI MCP Bridge - Grok",
        url="https://grok.com/c/a1db4d17-82fa-458a-80b5-a03332bfa25d?rid=abc",
    )

    assert match_fixed_tab(config, [tab]) is tab
    assert _fixed_chrome_tab_available(config, [tab])


def test_fixed_tab_matches_fresh_url_after_navigation():
    config = {
        "url": "https://chat.deepseek.com/",
        "fresh_url": "https://chat.deepseek.com/",
        "match_domains": ["chat.deepseek.com"],
        "browser_label": "DeepSeek / chat.deepseek.com",
        "provider": "DeepSeek",
    }
    tab = SimpleNamespace(title="DeepSeek", url="https://chat.deepseek.com/")

    assert _fixed_chrome_tab_available(config, [tab])


def test_cdp_tab_uses_provider_label_as_fallback():
    config = {
        "url": "https://agent.minimaxi.com/chat",
        "fresh_url": "https://agent.minimaxi.com/chat",
        "match_domains": ["agent.minimaxi.com"],
        "browser_label": "MiniMax Agent / agent.minimaxi.com",
        "provider": "MiniMax Agent",
    }
    tab = CDPTab(title="MiniMax Agent: 简单指令, 无限可能", url="https://agent.minimaxi.com/chat?id=398526514742292")

    assert match_cdp_tab(config, [tab]) is tab
