from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import models
from models import Transactions, Users
from typing import Annotated, Optional, Literal
from datetime import date as date_type
from database import engine, SessionLocal
from fastapi.responses import JSONResponse
from router import auth, admin
from router.auth import get_current_user

app = FastAPI()

class Transaction(BaseModel):
    title : str
    amount : float = Field(gt=0)
    type : Literal['income', 'expense']
    category : str
    date : date_type

class TransactionUpdate(BaseModel):
    title : Optional[str] = Field(default=None)
    amount : Optional[float] = Field(default=None, gt=0)
    type : Optional[Literal['income', 'expense']] = Field(default=None)
    category : Optional[str] = Field(default=None)
    date : Optional[date_type] = Field(default=None)

models.Base.metadata.create_all(bind=engine)
app.include_router(auth.router)
app.include_router(admin.router)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@app.post('/transactions', status_code=201)
def create_transaction(user: user_dependency, db : db_dependency, new_transaction : Transaction):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    transaction_model = Transactions(**new_transaction.model_dump(), owner_id = user.get('id'))
    db.add(transaction_model)
    db.commit()
    db.refresh(transaction_model)

    return transaction_model


@app.get('/transactions')
def read_transactions(user: user_dependency, db : db_dependency):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    return db.query(Transactions).filter(Transactions.owner_id == user.get('id')).all()


@app.get('/transactions/filter')
def filter_transactions(
    user: user_dependency,
    db : db_dependency,
    type : Optional[Literal['income', 'expense']] = None,
    category : Optional[str] = None,
    minimum_amount : Optional[float] = None,
    maximum_amount : Optional[float] = None
):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    query = db.query(Transactions).filter(Transactions.owner_id == user.get('id'))

    if type is not None:
        query = query.filter(Transactions.type == type)
    if category is not None:
        query = query.filter(Transactions.category == category)
    if minimum_amount is not None:
        query = query.filter(Transactions.amount >= minimum_amount)
    if maximum_amount is not None:
        query = query.filter(Transactions.amount <= maximum_amount)

    return query.all()


@app.get('/transactions/{transaction_id}')
def read_specific_transaction(user: user_dependency, db : db_dependency, transaction_id : int):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    specific_transaction = db.query(Transactions).filter(Transactions.owner_id == user.get('id')).filter(Transactions.id == transaction_id).first()
    if specific_transaction is not None:
        return specific_transaction
    else:
        raise HTTPException(status_code=404, detail='Transaction not found')


@app.put('/transactions/{transaction_id}')
def update_transaction(user: user_dependency, db : db_dependency, transaction_id : int, update_transaction : TransactionUpdate):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    transaction = db.query(Transactions).filter(Transactions.owner_id == user.get('id')).filter(Transactions.id == transaction_id).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail='Transaction not found')

    update_data = update_transaction.model_dump(exclude_unset=True)

    for key,value in update_data.items():
        setattr(transaction,key,value)

    db.commit()
    db.refresh(transaction)
    return transaction


@app.delete('/transactions/{transaction_id}')
def delete_transaction(user: user_dependency, db : db_dependency, transaction_id : int):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    transaction = db.query(Transactions).filter(Transactions.owner_id == user.get('id')).filter(Transactions.id == transaction_id).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail='Transaction not found')

    db.delete(transaction)
    db.commit()
    return JSONResponse(status_code=200, content={'message' : 'Transaction deleted successfully'})


@app.get('/user')
def get_user(user: user_dependency, db : db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    return db.query(Users).filter(Users.id == user.get('id')).first()