# app/campaigns/utils.py
def inject_placeholders(html: str, contact: dict) -> str:
    """
    Simple placeholder injection. Use cautiously — real projects should escape values.
    Expected placeholders: {{name}}, {{unsubscribe_link}}
    """
    out = html
    try:
        name = contact.get("name", "")
        unsubscribe = contact.get("unsubscribe_link") or f"https://example.com/unsubscribe/{contact.get('id','')}"
        out = out.replace("{{name}}", name)
        out = out.replace("{{unsubscribe_link}}", unsubscribe)
    except Exception:
        pass
    return out
