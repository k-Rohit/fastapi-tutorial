from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler
)
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from schemas import PostCreate, PostResponse, UserResponse, UserCreate, PostUpdate, UserUpdate


import models

from database import Base, engine, get_db

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from typing import Annotated
from datetime import datetime
from contextlib import asynccontextmanager


# When the application starts, create the database tables. Then pause at yield while the application runs. When the application is shutting down, resume after yield and dispose of the database engine.
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")

@app.get("/",tags=["Home"], include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts") # here we have stacked the decorators to make the same function respond to two different routes
# include_in_schema=False is used to hide the route from the documentation page
async def home(request: Request, db: Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = result.scalars().all()
    return templates.TemplateResponse(request, 'home.html', context={"posts": posts, "title" : "Home"})

@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.Post)
                    .options(selectinload(models.Post.author))
                    .where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Post not found",)

@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(request: Request, user_id: int, db: Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    result = await db.execute(select(models.Post)
                              .options(selectinload(models.Post.author))
                              .where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        'user_posts.html',
        {"posts": posts, "user" : user, "title" : f"{user.username}'s Posts"}
    )

@app.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["User"])
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.username == user.username))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with username '{user.username}' already exists."
        )
        
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    existing_email = result.scalars().first()

    if existing_email:
        raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail=f"Email already exists.",
    )
    
    new_user = models.User(
        username = user.username,
        email = user.email,
    )  
    
    db.add(new_user) # stages the insert
    await db.commit() # saves it into the db
    await db.refresh(new_user) # reloads the object from the database
    
    return new_user
       
@app.get("/api/users/{user_id}", response_model=UserResponse, tags=["User"])
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse], tags=["User"])
async def get_user_posts(user_id, db: Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    result = await db.execute(select(models.Post)
                            .options(selectinload(models.Post.author))
                            .where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts

@app.patch("/api/users/{user_id}", response_model=UserResponse, tags=["User"])
async def update_user(user_id: int, user_update: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found")
    
    if user_update.username is not None and user_update.username != user.username:
        result = await db.execute(select(models.User).where(models.User.username == user_update.username))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    
    if user_update.email is not None and user_update.email != user.email:
        result = await db.execute(select(models.User).where(models.User.email == user_update.email))
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.image_file is not None:
        user.image_file = user_update.image_file
    
    await db.commit()
    await db.refresh(user)
    return user

@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["User"])
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    await db.delete(user)
    await db.commit()

@app.get("/api/posts", tags=["Posts"], response_model=list[PostResponse])
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)))
    posts = result.scalars().all()
    return posts
    
@app.post("/api/posts", tags=["Posts"], response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, db: Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == post.user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    new_post = models.Post(
        title = post.title,
        content = post.content,
        user_id = post.user_id
    )
    
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])
    return new_post

@app.get("/api/posts/{post_id}", tags=["Posts"], response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {post_id} not found")

@app.put("/api/posts/{post_id}", tags=["Posts"], response_model=PostResponse)
async def update_post_full(post_id: int, post_data: PostCreate, db: Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {post_id} not found")
    
    if post_data.user_id != post.user_id:
        # if its not the same then check for whichever user they are trying to assign
        # the post that even exixts or not.
        result = await db.execute(select(models.User).options(selectinload(models.Post.author)).where(models.User.id == post_data.user_id))
        user = result.scalars().first()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id
    
    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post

@app.patch("/api/posts/{post_id}", tags=["Posts"], response_model=PostResponse)
async def update_post_partial(post_id: int, post_data: PostUpdate, db: Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {post_id} not found")

    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)
    
    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


@app.delete("/api/posts/{post_id}", tags=["Posts"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, db: Annotated[AsyncSession,Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {post_id} not found")
    
    await db.delete(post)
    await db.commit()
 
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)
    return templates.TemplateResponse(
        request,
        'error.html',
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request please check your input and try again."
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
    )

@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    message = (
    exception.detail
    if exception.detail
    else "An error occurred. Please check you request and try again")
    
    return templates.TemplateResponse(
        request,
        'error.html',
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message
        },
        status_code=exception.status_code
    )

