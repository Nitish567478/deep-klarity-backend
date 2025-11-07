from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Question(BaseModel):
    question: str
    choices: Optional[List[str]] = None
    answer: Optional[str] = None

class QuizOutput(BaseModel):
    topic: str
    description: Optional[str] = None
    questions: List[Question]
    source_text: Optional[str] = None
    generated_at: Optional[datetime] = None
