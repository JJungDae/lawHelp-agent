from pydantic import BaseModel


class RetrievedDocument(BaseModel):
    id: str
    question: str
    answer: str
    category: str
