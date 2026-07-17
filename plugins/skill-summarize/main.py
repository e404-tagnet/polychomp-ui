async def on_load(config):
    pass

async def post_receive(response: str, context: dict) -> str | None:
    # If user asked for a summary, provide a compact version
    user_msg = context.get("last_user_message", "").lower()
    if any(kw in user_msg for kw in ["summarize", "tl;dr", "summary", "summarise"]):
        max_len = config.get("max_length", 200)
        if len(response) > max_len:
            # Simple extractive summary: first sentence + bullet of key lines
            lines = [l.strip() for l in response.splitlines() if l.strip()]
            bullets = lines[:5]
            if len(bullets) > 3:
                bullets = bullets[:3]
            summary = "**Summary:**\n" + "\n".join(f"• {b[:120]}" for b in bullets)
            return summary
    return None

async def handle_summarize(cmd: str, args: str, context: dict) -> str:
    return f"[Summarize command received with args: {args}]"

config = {}
