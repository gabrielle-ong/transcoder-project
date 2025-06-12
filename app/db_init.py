import time
from sqlalchemy.exc import OperationalError

# We must import all models so that Base knows about them
from .database import engine, Base
from .models import Files, Transactions, Codec, ProcessingStatus, TransactionType

def main():
    # Checks that DB PostgreSQL is ready before api and worker containers connects to db container
    # retry for race condition where app or worker starts before DB is ready
    # note: `depends on` docker compose flag just ensures container is created but psql may not be setup
    db_ready = False
    max_retries = 10
    retry_count = 0

    print("--- ATTEMPTING TO CONNECT TO DATABASE ---")

    while not db_ready and retry_count < max_retries:
        try:
            # Try to establish a connection and create tables
            # if tables already exist, wont recreate
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
        exit(1)

if __name__ == "__main__":
    main()
