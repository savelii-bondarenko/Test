from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from mistralai import Mistral
import os
from dotenv import load_dotenv

from app.database import SessionLocal, init_db, ChatSession, ChatMessage
import app.schemas as schemas
import app.utils as utils

load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")
MODEL_NAME = "mistral-small-latest"
client = Mistral(api_key=api_key)

app = FastAPI(title="Mistral Chat API")

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/chats", response_model=schemas.SessionResponse)
def create_chat_session(db: Session = Depends(get_db)):
    new_session = ChatSession()
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@app.post("/chats/{chat_id}/messages", response_model=schemas.MessageResponse)
def send_message(chat_id: int, message: schemas.MessageCreate, db: Session = Depends(get_db)):

    session = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    history = db.query(ChatMessage).filter(ChatMessage.session_id == chat_id).order_by(ChatMessage.timestamp).all()

    messages_payload = [{"role": msg.role, "content": msg.content} for msg in history]
    messages_payload.append({"role": "user", "content": message.content})

    chat_response = client.chat.complete(
        model=MODEL_NAME,
        messages=messages_payload
    )

    ai_content = chat_response.choices[0].message.content
    usage = chat_response.usage

    pricing = utils.PRICING.get(MODEL_NAME)
    input_cost = usage.prompt_tokens * pricing["input"]
    output_cost = usage.completion_tokens * pricing["output"]

    user_msg = ChatMessage(
        session_id=chat_id,
        role="user",
        content=message.content,
        tokens_used=usage.prompt_tokens,
        cost=input_cost
    )

    ai_msg = ChatMessage(
        session_id=chat_id,
        role="assistant",
        content=ai_content,
        tokens_used=usage.completion_tokens,
        cost=output_cost
    )

    db.add(user_msg)
    db.add(ai_msg)

    session.total_cost += (input_cost + output_cost)

    db.commit()
    db.refresh(ai_msg)

    return ai_msg

@app.get("/chats/{chat_id}", response_model=schemas.SessionResponse)
def get_chat_history(chat_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session

@app.get("/chats/{chat_id}/tokens")
def get_chat_tokens(chat_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"Session Id": session.id,
            "Created at": session.created_at,
            "Total tokens cost": session.total_cost}

@app.delete("/chats/{chat_id}")
def delete_chat_session(chat_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == chat_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    db.delete(session)
    db.commit()
    return {"detail": "Session deleted"}