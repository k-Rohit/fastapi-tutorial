from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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

@app.get("/",tags=["Home"], include_in_schema=False)
@app.get("/posts", include_in_schema=False) # here we have stacked the decorators to make the same function respond to two different routes

# include_in_schema=False is used to hide the route from the documentation page
def home(request: Request):
    return templates.TemplateResponse(request, 'home.html', context={"posts": posts, "title" : "Home"})

@app.get("/api/posts", tags=["Posts"])
def get_posts():
    return posts



