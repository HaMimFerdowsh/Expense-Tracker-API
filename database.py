from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

SQLALCHEMY_DATABASE_URL = 'postgresql://transactions_db_ygm8_user:8JSESj4KCMTD6ZxUrkklofszqA4oJ8lo@dpg-db4hq6ei0phs73cnkc8g-a.singapore-postgres.render.com/transactions_db_ygm8'

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)

Base = declarative_base()