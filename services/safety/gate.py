import logging
import aiohttp
from shared.models import ModerationResult, PersonaConfig
from shared.config import get_settings

settings = get_settings()
log = logging.getLogger("safety")

BLOCKED_PHRASES = [
    "i guarantee", "100% sure", "definitely will",
    "legal action", "lawyer",
    "competitor is terrible", "competitor sucks",
]

async def run_safety_gate(content: str, persona: PersonaConfig) -> ModerationResult:
    flags = []

    kw = _keyword_filter(content)
    if not kw["passed"]:
        return ModerationResult(passed=False, flags=kw["flags"],
                                reason=f"Blocked phrase: {kw['flags']}")

    perspective_score = await _perspective_check(content)
    if perspective_score > settings.safety_threshold:
        return ModerationResult(passed=False, perspective_score=perspective_score,
                                flags=["high_toxicity"],
                                reason=f"Toxicity {perspective_score:.2f} exceeds {settings.safety_threshold}")

    for avoid in persona.avoid_topics:
        if avoid.lower() in content.lower():
            flags.append(f"avoid_topic:{avoid}")

    return ModerationResult(passed=True, perspective_score=perspective_score, flags=flags,
                            reason="Passed" if not flags else f"Passed with warnings: {flags}")

def _keyword_filter(content: str) -> dict:
    content_lower = content.lower()
    triggered = [p for p in BLOCKED_PHRASES if p in content_lower]
    return {"passed": len(triggered) == 0, "flags": triggered}

async def _perspective_check(content: str) -> float:
    if not settings.perspective_api_key or settings.perspective_api_key.startswith("your_"):
        return 0.0
    url = f"https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key={settings.perspective_api_key}"
    payload = {"comment": {"text": content}, "requestedAttributes": {"TOXICITY": {}}, "languages": ["en"]}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["attributeScores"]["TOXICITY"]["summaryScore"]["value"]
    except Exception as e:
        log.warning(f"Perspective API error: {e}")
    return 0.0
