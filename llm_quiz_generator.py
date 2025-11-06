import os
import json
import logging
import re
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in environment")

import gemini
gemini.api_key = GEMINI_API_KEY

logger = logging.getLogger("gemini_quiz_generator")
logger.setLevel(logging.INFO)

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
'''

def generate_quiz_from_text(topic: str, source_text: str, num_questions: int = 5) -> Dict[str, Any]:
    prompt = PROMPT_TEMPLATE.format(
        topic=topic,
        source_text=source_text or "No source provided",
        num_questions=num_questions
    )

    try:
        response = gemini.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1200,
        )
    except Exception as e:
        logger.error("Gemini API request failed: %s", e)
        raise RuntimeError(f"Gemini API request failed: {str(e)}")

    text = response['choices'][0]['message']['content'].strip()

    try:
        payload = json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            try:
                payload = json.loads(m.group(0))
            except Exception as e:
                logger.error("Failed to parse JSON from regex match: %s", e)
                raise RuntimeError(f"LLM returned invalid JSON. Raw output: {text}")
        else:
            logger.error("LLM did not return valid JSON. Raw output: %s", text)
            raise RuntimeError("LLM did not return valid JSON. Raw output: " + text)

    if 'questions' not in payload or not isinstance(payload['questions'], list):
        raise RuntimeError("LLM JSON missing 'questions' field or it is not a list")

    for q in payload['questions']:
        q.setdefault('choices', ['A','B','C','D'])
        q.setdefault('answer', q['choices'][0] if q['choices'] else 'A')

    return payload
