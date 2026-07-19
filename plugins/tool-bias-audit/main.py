"""Bias Audit plugin — runs PRISM keyword classifier on AI responses too."""
import re
from typing import Dict, Any

# AI-specific bias keywords (sycophancy, overconfidence, anchoring in its OWN output)
AI_BIAS_KEYWORDS: Dict[str, list] = {
    "ai_sycophancy": [
        r"\byou\s+are\s+right\b", r"\bgreat\s+point\b", r"\bexactly\b",
        r"\babsolutely\b", r"\bdefinitely\b", r"\bi\s+completely\s+agree\b",
        r"\byour\s+intuition\b", r"\byou\s+said\s+it\b",
    ],
    "ai_overconfidence": [
        r"\bi\s+am\s+certain\b", r"\bthe\s+answer\s+is\b", r"\bthis\s+is\s+correct\b",
        r"\bundeniable\b", r"\bwithout\s+doubt\b", r"\bguaranteed\b",
    ],
    "ai_courtesy": [
        r"\bi\s+do\s+not\s+want\s+to\s+argue\b", r"\blet's\s+agree\b",
        r"\bwe\s+can\s+agree\b", r"\bi\s+see\s+your\s+point\b", r"\bfair\s+enough\b",
    ],
    "ai_anchoring": [
        r"\bas\s+i\s+said\b", r"\bgoing\s+back\s+to\b", r"\breferring\s+to\b",
        r"\bmy\s+previous\b", r"\bearlier\s+i\b",
    ],
}

def _score(text: str, map: Dict[str, list]) -> Dict[str, float]:
    text_lower = text.lower()
    scores = {}
    for bias, patterns in map.items():
        hits = sum(1 for p in patterns if re.search(p, text_lower))
        scores[bias] = min(hits / max(len(patterns) * 0.3, 1.0), 1.0)
    return scores

def on_load(ctx: Dict[str, Any]):
    pass

def post_receive(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the AI response for its own biases."""
    ai_text = ctx.get("response", "")
    if not ai_text:
        return ctx

    scores = _score(ai_text, AI_BIAS_KEYWORDS)
    dominant = max(scores, key=scores.get) if scores else None
    confidence = scores.get(dominant, 0.0) if dominant else 0.0

    # Attach audit metadata
    if "prism_meta" not in ctx:
        ctx["prism_meta"] = {}
    ctx["prism_meta"]["ai_audit"] = {
        "scores": scores,
        "dominant": dominant,
        "confidence": confidence,
    }
    return ctx
