from sqlalchemy.orm import Session
from app.database import ChatSession, ChatMessage

def create_session(db: Session) -> ChatSession:
    new_session = ChatSession()
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

def get_session(db: Session, chat_id: int) -> ChatSession | None:
    return db.query(ChatSession).filter(ChatSession.id == chat_id).first()

def delete_session(db: Session, chat_id: int) -> bool:
    session = get_session(db, chat_id)
    if session:
        db.delete(session)
        db.commit()
        return True
    return False

def update_session_cost(db: Session, session: ChatSession, cost: float):
    session.total_cost += cost
    db.commit()


def get_session_messages(db: Session, chat_id: int):
    return db.query(ChatMessage).filter(ChatMessage.session_id == chat_id).order_by(ChatMessage.timestamp).all()

def create_message(db: Session, message_data: dict) -> ChatMessage:
    new_message = ChatMessage(**message_data)
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message