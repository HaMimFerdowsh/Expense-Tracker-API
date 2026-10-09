from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
from typing import Annotated, Optional
from database import SessionLocal
from models import Users
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError

router = APIRouter()

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
OAuth2_bearer = OAuth2PasswordBearer(tokenUrl='login')

SECRET_KEY = 'af1ccd492110872d63bd2162fb67953e9f2362cd283c566d055e39d3134d9590'
ALGORITHM = 'HS256'

class CreateUsers(BaseModel):
    username : str
    email : str
    password : str

class UpdateUser(BaseModel):
    username : Optional[str] = Field(default=None)
    email : Optional[str] = Field(default=None)

class UpdatePassword(BaseModel):
    current_password : str
    new_password: str


def authenticate_user(username, password, db):
    user = db.query(Users).filter(Users.username == username).first()
    if user is None:
        return False
    if bcrypt_context.verify(password, user.hashed_password):
        return user
    return False

def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id, 'role': role}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: Annotated[str, Depends(OAuth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: int = payload.get('id')
        role: str = payload.get('role')
        if username is None or user_id is None:
            raise HTTPException(status_code=401, detail='Could not validate user')
        return {'username': username, 'id': user_id, 'role': role}
    except JWTError:
        raise HTTPException(status_code=401, detail='Could not validate user')


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post('/createuser')
def create_users(db : db_dependency, new_user : CreateUsers):

    existing_user = db.query(Users).filter(Users.username == new_user.username).first()
    if existing_user is not None:
        raise HTTPException(status_code=400, detail='Username already exists')

    user_model = Users(
        username = new_user.username,
        email = new_user.email,
        hashed_password = bcrypt_context.hash(new_user.password),
        role = 'user'
    )

    db.add(user_model)
    db.commit()

    return JSONResponse(status_code=201, content={'message' : 'User created successfully'})


@router.post('/login')
def login_user(db : db_dependency, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):

    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid username or password')

    token = create_access_token(user.username, user.id, user.role, timedelta(minutes=30))
    return {'access_token': token, 'token_type': 'bearer'}


@router.put('/edituser')
def update_user(user: user_dependency, db : db_dependency, update_user : UpdateUser):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    user = db.query(Users).filter(Users.id == user.get('id')).first()

    update_data = update_user.model_dump(exclude_unset=True)

    new_username = update_data.get('username')
    if new_username is not None:
        taken = db.query(Users).filter(Users.username == new_username).filter(Users.id != user.id).first()
        if taken is not None:
            raise HTTPException(status_code=400, detail='Username already exists')

    for key,value in update_data.items():
        setattr(user,key,value)

    db.commit()
    return JSONResponse(status_code=200, content={'message' : 'User updated successfully'})


@router.put('/passwordchange')
def update_password(user: user_dependency, db : db_dependency, update_password : UpdatePassword):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    user = db.query(Users).filter(Users.id == user.get('id')).first()

    if not bcrypt_context.verify(update_password.current_password, user.hashed_password):
        raise HTTPException(status_code=401, detail='Wrong Password')

    user.hashed_password = bcrypt_context.hash(update_password.new_password)

    db.add(user)
    db.commit()
    return JSONResponse(status_code=200, content={'message' : 'Password updated successfully'})