"""Draft a short read-along story with the local model, for the Sulat book editor.

The teacher always edits the draft and records it; nothing here is saved.
"""

import json
import re
import string

from app.plans import PROMPTS_DIR, OllamaSettings, PlanError, _post_generate

TOPICS = {
    "fil": {"bukid": "bukid", "pamilya": "pamilya", "hayop": "hayop", "kalikasan": "kalikasan", "paaralan": "paaralan"},
    "eng": {"bukid": "the farm", "pamilya": "family", "hayop": "animals", "kalikasan": "nature", "paaralan": "school"},
}
IDEA_LINE = {"fil": "Ideya ng guro: $idea\n", "eng": "The teacher's idea: $idea\n"}
STORY_OPTIONS = {"temperature": 0.2, "num_predict": 300, "repeat_penalty": 1.15}
STORY_SEEDS = (7, 21)
MAX_WORDS = 80
MAX_IDEA_CHARS = 200


def build_story_prompt(topic: str, language: str, idea: str = "") -> str:
    if language not in TOPICS:
        raise ValueError("stories can be drafted in Filipino (fil) or English (eng) only")
    if topic not in TOPICS[language]:
        raise ValueError(f"topic must be one of {', '.join(TOPICS[language])}")
    idea = " ".join(idea.split())[:MAX_IDEA_CHARS]
    template = string.Template((PROMPTS_DIR / f"story-{language}.txt").read_text(encoding="utf-8"))
    idea_line = string.Template(IDEA_LINE[language]).substitute(idea=idea) if idea else ""
    return template.substitute(topic=TOPICS[language][topic], idea=idea_line)


def check_story(raw: str) -> dict:
    """The model's reply as {"title", "text"}, or a PlanError saying what was wrong with it."""
    try:
        story = json.loads(raw)
    except json.JSONDecodeError:
        raise PlanError("the model's story was not valid JSON") from None
    if not isinstance(story, dict):
        raise PlanError("the model's story was not a JSON object")
    title = " ".join(str(story.get("title") or "").split()).strip('"')
    text = " ".join(str(story.get("text") or "").split())
    if not title or not text:
        raise PlanError("the model's story had no title or no text")
    if len(text.split()) > MAX_WORDS:
        raise PlanError(f"the model's story was over {MAX_WORDS} words")
    # Words with no letters get zero-length times in a book's model reading.
    if re.search(r"\d", text):
        raise PlanError("the model's story had digits")
    return {"title": title, "text": text}


def draft_story(topic: str, language: str, idea: str = "", settings: OllamaSettings | None = None) -> dict:
    """A {"title", "text"} draft. Raises ValueError for bad input, PlanError if no usable draft came back."""
    prompt = build_story_prompt(topic, language, idea)
    settings = settings or OllamaSettings.from_env()
    error = None
    for seed in STORY_SEEDS:
        reply = _post_generate(prompt, settings, seed, options=STORY_OPTIONS, format="json")
        try:
            return check_story(reply.get("response", ""))
        except PlanError as err:
            error = err
    raise error
