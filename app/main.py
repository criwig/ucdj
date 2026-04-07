from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

from .database import Base, engine  # noqa: E402 — after load_dotenv
from .routes import admin, game, player

templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Undercovid DJ", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(game.router)
app.include_router(admin.router)
app.include_router(player.router)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request, "404.html", status_code=404)
