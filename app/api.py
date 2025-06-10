from fastapi import FastAPI
from .database import init_db
# db_init race condition - need to import models so that init_db creates Files and Transactions models
from . import models

# Create DB tables on startup, checks that db container is ready (race condition bug)
init_db()

app = FastAPI()

@app.get("/")
def root():
    return "Hello, World!"