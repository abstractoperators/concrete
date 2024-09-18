from pydantic import BaseModel


class CommonReadParameters(BaseModel):
    skip: int
    limit: int
