from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime

# user schema

class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=120)
    

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    image_file: str | None
    image_path: str 

class UserCreate(UserBase):
    pass

# posts schema
class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)

class PostCreate(PostBase):
    user_id: int # TEMPORARY 

class PostResponse(PostBase):
    model_config = ConfigDict(
        from_attributes=True
    )
    
    id: int
    user_id: int
    date_posted: datetime
    author: UserResponse

