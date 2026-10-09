from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated
from database import SessionLocal
from models import Users, Transactions
from fastapi.responses import JSONResponse
from router.auth import get_current_user

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get('/admin/users')
def read_all_users(user: user_dependency, db: db_dependency):

    if user is None or user.get('role') != 'admin':
        raise HTTPException(status_code=401, detail='Failed Authentication')

    users = db.query(Users).all()

    return [{'id': u.id, 'username': u.username, 'email': u.email, 'role': u.role} for u in users]


@router.get('/admin/transactions')
def read_all_transactions(user: user_dependency, db: db_dependency):

    if user is None or user.get('role') != 'admin':
        raise HTTPException(status_code=401, detail='Failed Authentication')

    return db.query(Transactions).all()


@router.delete('/admin/delete_transaction/{transaction_id}')
def delete_any_transaction(user: user_dependency, db: db_dependency, transaction_id: int):

    if user is None or user.get('role') != 'admin':
        raise HTTPException(status_code=401, detail='Failed Authentication')

    transaction = db.query(Transactions).filter(Transactions.id == transaction_id).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail='Transaction not found')

    db.delete(transaction)
    db.commit()

    return JSONResponse(status_code=200, content={'message': 'Transaction deleted successfully'})


@router.delete('/admin/delete_user/{user_id}')
def delete_user(user: user_dependency, db: db_dependency, user_id: int):

    if user is None or user.get('role') != 'admin':
        raise HTTPException(status_code=401, detail='Failed Authentication')

    if user.get('id') == user_id:
        raise HTTPException(status_code=400, detail='Admin cannot delete own account')

    target_user = db.query(Users).filter(Users.id == user_id).first()
    if target_user is None:
        raise HTTPException(status_code=404, detail='User not found')

    db.query(Transactions).filter(Transactions.owner_id == user_id).delete()
    db.delete(target_user)
    db.commit()

    return JSONResponse(status_code=200, content={'message': 'User deleted successfully'})