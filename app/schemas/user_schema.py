from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    secret_key: str

class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str

class LoginSchema(BaseModel):
    email: EmailStr
    password: str
