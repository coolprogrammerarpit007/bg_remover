from fastapi import FastAPI
from pydantic import BaseModel,Field
from uuid import UUID

app = FastAPI()

class Book(BaseModel):
    id:UUID
    title:str = Field(min_length = 1)
    author:str = Field(min_length = 1,max_length = 100)
    description:str = Field(min_length = 1,max_length = 200)
    rating:int = Field(gt = -1,lt = 6)




@app.get("/")

async def read_api():
    return {"msg":"Welcome Abroad!"}


@app.get("/user/{name}")

async def get_name(name:str):
    return {"name":name.title()}


Books = []

@app.post("/")
def create_book(book:Book):
    Books.append(book)
    return {"msg":"Book created successfully!","data":book}


@app.get("/get-books")

def get_books():
    return {"books":Books}