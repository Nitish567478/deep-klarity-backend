import os
import json
import logging
import re
from typing import Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in environment")

genai.configure(api_key=GEMINI_API_KEY)

logger = logging.getLogger("gemini_quiz_generator")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

PROMPT_TEMPLATE = '''
You are a helpful assistant that produces a quiz (topic: {topic}).
Use the source text delimited by triple backticks as background knowledge.
Respond with valid JSON only (no additional explanation). The JSON should follow this schema:
{{
  "topic": "<topic>",
  "description": "<short description of topic>",
  "questions": [
    {{"question": "...", "choices": ["A","B","C","D"], "answer": "A"}}
  ],
  "source_text": "<optional short excerpt>"
}}

Background:
Generate {num_questions} questions. Prefer multiple-choice with 4 options when possible, otherwise short answer.
Be concise in question wording. Ensure answers are correct according to the source.

Source text:
'''

def get_working_model() -> str:
    try:
        models = [m.name for m in genai.list_models()]
        preferred = [
            "models/gemini-pro-latest",
            "models/gemini-flash-latest",
            "models/gemini-2.5-flash",
            "models/gemini-2.5-pro"
        ]
        for name in preferred:
            if name in models:
                logger.info(f"Using model: {name}")
                return name
        raise RuntimeError(f"No supported Gemini models found. Available: {models}")
    except Exception as e:
        raise RuntimeError(f"Failed to list Gemini models: {e}")

def generate_quiz_from_text(topic: str, source_text: str, num_questions: int = 5) -> Dict[str, Any]:
    prompt = PROMPT_TEMPLATE.format(
        topic=topic,
        source_text=source_text or "No source provided",
        num_questions=num_questions
    )

    model_name = get_working_model()

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        text = response.text.strip()
    except Exception as e:
        logger.error("Gemini API request failed: %s", e)
        raise RuntimeError(f"Gemini API request failed: {str(e)}")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                raise RuntimeError(f"LLM returned invalid JSON. Raw output: {text}")
        else:
            raise RuntimeError("LLM did not return valid JSON. Raw output: " + text)

    if 'questions' not in payload or not isinstance(payload['questions'], list):
        raise RuntimeError("LLM JSON missing 'questions' field or it is not a list")

    for q in payload['questions']:
        q.setdefault('choices', ['A', 'B', 'C', 'D'])
        q.setdefault('answer', q['choices'][0] if q['choices'] else 'A')

    return payload

if __name__ == "__main__":
    topic = "Solar System"
    source_text = """
    The Solar System consists of the Sun and the celestial objects bound to it by gravity,
    including eight planets, their moons, and smaller bodies such as dwarf planets and asteroids.
    """
    try:
        quiz = generate_quiz_from_text(topic, source_text, num_questions=5)
        print(json.dumps(quiz, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error("Error: %s", e)
