from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import os
import time

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# db_init race condition
# Checks that DB PostgreSQL is ready before fastapi container connects to db container
# depends on docker compose flag just ensures container is created but psql may not be setup
def init_db():
    db_ready = False
    max_retries = 10
    retry_count = 0

    print("--- ATTEMPTING TO CONNECT TO DATABASE ---")

    while not db_ready and retry_count < max_retries:
        try:
            # Try to establish a connection and create tables
            Base.metadata.create_all(bind=engine)
            db_ready = True
            print("--- DATABASE IS READY AND TABLES ARE CREATED ---")
        except OperationalError as e:
            retry_count += 1
            print(f"--- DATABASE NOT READY (Attempt {retry_count}/{max_retries}). Retrying in 2 seconds... ---")
            print(f"Error: {e}")
            time.sleep(2)

    if not db_ready:
        print("--- DATABASE FAILED TO STARTUP AFTER MULTIPLE RETRIES. EXITING. ---")
        # In a real application, you might want to exit or raise a more critical error
        exit(1)