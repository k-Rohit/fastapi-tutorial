from fastapi import FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

posts: list[dict] = [
    {
        "id" : 1,
        "author": "Rohit",
        "title": "FastAPI is Awsome",
        "content" : "The is a ASGI web framework",
        "date_posted" : "August 16, 2026"
    },

    {
        "id" : 2,
        "author": "Shweta",
        "title": "Databricks is Awsome",
        "content" : "The is a data analytics and processing platform",
        "date_posted" : "August 17, 2026"
    }
]

@app.get("/",tags=["Home"], include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts") # here we have stacked the decorators to make the same function respond to two different routes
# include_in_schema=False is used to hide the route from the documentation page
def home(request: Request):
    return templates.TemplateResponse(request, 'home.html', context={"posts": posts, "title" : "Home"})

@app.get("/posts/{post_id}", include_in_schema=False)
def get_post_by_id(request: Request,
             post_id: int):
    for post in posts:
        if post.get("id") == post_id:
            title = post.get('title','Title Not found')[:50]
            return templates.TemplateResponse(
                request,
                'post.html',
                {"post" : post, "title": title})
    # place outside the loop
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Post with id {post_id} not found"
            )
            
@app.get("/api/posts", tags=["Posts"])
def get_posts():
    return posts

@app.get("/api/posts/{post_id}", tags=["Posts"])
def get_post(post_id: int):
    for post in posts:
        if post["id"] == post_id:
            return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {post_id} not found")

@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail" : exception.errors()}
        )
    
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
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail 
        if exception.detail
        else "An error occurred. Please check you request and try again"
    )
    
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code = exception.status_code,
            content={"detail": message},
        )
    
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


