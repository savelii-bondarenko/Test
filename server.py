from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from mistralai import Mistral
from mistralai.models import SDKError
import os
from dotenv import load_dotenv
from fastapi.responses import RedirectResponse

from app.database import SessionLocal, init_db
import app.schemas as schemas
import app.utils as utils
import app.data_op as crud

load_dotenv()

api_key = os.getenv("MISTRAL_API_KEY")
MODEL_NAME = "mistral-tiny"


if not api_key:
    raise ValueError("MISTRAL_API_KEY is not set in environment variables")

client = Mistral(api_key=api_key)

app = FastAPI(title="Mistral Chat API")

init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

@app.post("/chats", response_model=schemas.SessionResponse)
def create_chat_session(db: Session = Depends(get_db)):
    return crud.create_session(db)

@app.post("/chats/{chat_id}/messages", response_model=schemas.MessageResponse)
def send_message(chat_id: int, message: schemas.MessageCreate, db: Session = Depends(get_db)):

    session = crud.get_session(db, chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    history = crud.get_session_messages(db, chat_id)
    messages_payload = [{"role": msg.role, "content": msg.content} for msg in history]
    messages_payload.append({"role": "user", "content": message.content})

    try:
        chat_response = client.chat.complete(
            model=MODEL_NAME,
            messages=messages_payload
        )
    except SDKError as e:
        print(f"Mistral API Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Provider Error: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )

    ai_content = chat_response.choices[0].message.content
    usage = chat_response.usage
    pricing = utils.PRICING.get(MODEL_NAME)

    input_cost = usage.prompt_tokens * pricing["input"]
    output_cost = usage.completion_tokens * pricing["output"]
    total_interaction_cost = input_cost + output_cost

    crud.create_message(db, {
        "session_id": chat_id,
        "role": "user",
        "content": message.content,
        "tokens_used": usage.prompt_tokens,
        "cost": input_cost
    })

    ai_msg = crud.create_message(db, {
        "session_id": chat_id,
        "role": "assistant",
        "content": ai_content,
        "tokens_used": usage.completion_tokens,
        "cost": output_cost
    })

    crud.update_session_cost(db, session, total_interaction_cost)
    return ai_msg

@app.get("/chats/{chat_id}", response_model=schemas.SessionResponse)
def get_chat_history(chat_id: int, db: Session = Depends(get_db)):
    session = crud.get_session(db, chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session

@app.get("/chats/{chat_id}/tokens")
def get_chat_tokens(chat_id: int, db: Session = Depends(get_db)):
    session = crud.get_session(db, chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat not found")

    return {
        "Session Id": session.id,
        "Created at": session.created_at,
        "Total tokens cost": session.total_cost
    }

@app.delete("/chats/{chat_id}")
def delete_chat_session(chat_id: int, db: Session = Depends(get_db)):
    success = crud.delete_session(db, chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"detail": "Session deleted"}