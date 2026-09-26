from pydantic import BaseModel


class ProblemDto(BaseModel):
    type: str
    title: str
    status: int
    code: str
    detail: str
    request_id: str

