from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware    
from pydantic import BaseModel
from typing import Optional
import database, models, scraper, llm_quiz_generator
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os, json

load_dotenv()

database.init_db()
app = FastAPI(title="DeepKlarity Technologies")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

class GenerateRequest(BaseModel):
    topic: str
    num_questions: Optional[int] = 5
    use_wikipedia: Optional[bool] = True

@app.post('/generate')
async def generate_quiz(req: GenerateRequest, db: Session = Depends(get_db)):
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic must not be empty")

    source = ''
    if req.use_wikipedia:
        try:
            source = scraper.fetch_wikipedia_intro(topic)
        except Exception:
            source = ''

    try:
        payload = llm_quiz_generator.generate_quiz_from_text(topic, source, num_questions=req.num_questions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    db_item = database.Quiz(topic=topic, raw_output=json.dumps(payload))
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    return payload

@app.get('/history')
def get_history(limit: int = 20, db: Session = Depends(get_db)):
    items = db.query(database.Quiz).order_by(database.Quiz.generated_at.desc()).limit(limit).all()
    result = []
    for it in items:
        try:
            out = json.loads(it.raw_output)
        except Exception:
            out = {"raw_output": it.raw_output}
        out['id'] = it.id
        out['topic'] = it.topic
        out['generated_at'] = it.generated_at.isoformat()
        result.append(out)
    return result

@app.get('/health')
def health():
    return {"status": "ok"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('backend.main:app', host='0.0.0.0', port=int(os.getenv('PORT', 8000)), reload=True)
