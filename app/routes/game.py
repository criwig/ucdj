import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..email_helper import send_welcome_email
from ..models import Game, Player, Slot, SlotField
from ..slug import generate_slug

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.post("/games")
async def create_game(request: Request, db: Session = Depends(get_db)):
    form = await request.form()

    title = (form.get("title") or "").strip()
    if not title:
        return templates.TemplateResponse(
            request, "index.html", {"error": "Please enter a game title."}
        )

    slot_count = int(form.get("slot_count") or 0)
    if slot_count == 0:
        return templates.TemplateResponse(
            request, "index.html", {"error": "Please add at least one category."}
        )

    # Generate a unique slug, retry on collision (astronomically rare)
    for _ in range(10):
        slug = generate_slug()
        if not db.query(Game).filter(Game.slug == slug).first():
            break

    def parse_deadline(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None

    submission_deadline = parse_deadline(form.get("submission_deadline"))
    guessing_deadline = parse_deadline(form.get("guessing_deadline"))

    game = Game(
        admin_token=str(uuid.uuid4()),
        slug=slug,
        title=title,
        submission_deadline=submission_deadline,
        guessing_deadline=guessing_deadline,
    )
    db.add(game)
    db.flush()

    for i in range(slot_count):
        slot_name = (form.get(f"slot_{i}_name") or "").strip()
        if not slot_name:
            continue

        slot = Slot(game_id=game.id, name=slot_name, order=i)
        db.add(slot)
        db.flush()

        field_count = int(form.get(f"slot_{i}_field_count") or 0)
        for j in range(field_count):
            field_name = (form.get(f"slot_{i}_field_{j}_name") or "").strip()
            if not field_name:
                continue
            field_type = form.get(f"slot_{i}_field_{j}_type") or "text"
            required = form.get(f"slot_{i}_field_{j}_required") == "on"
            db.add(SlotField(
                slot_id=slot.id,
                name=field_name,
                field_type=field_type,
                required=required,
                order=j,
            ))

    db.commit()
    return RedirectResponse(url=f"/admin/{game.admin_token}", status_code=303)


@router.get("/game/{slug}/join", response_class=HTMLResponse)
async def join_page(request: Request, slug: str, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.slug == slug).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return templates.TemplateResponse(request, "join.html", {"game": game})


@router.post("/game/{slug}/join")
async def join_game(request: Request, slug: str, db: Session = Depends(get_db)):
    form = await request.form()
    name = (form.get("name") or "").strip()
    email = (form.get("email") or "").strip().lower()

    game = db.query(Game).filter(Game.slug == slug).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if game.state != "collecting":
        return templates.TemplateResponse(
            request,
            "join.html",
            {"game": game, "error": "This game is no longer accepting new players."},
        )

    if game.submission_deadline and datetime.now() > game.submission_deadline:
        return templates.TemplateResponse(
            request,
            "join.html",
            {"game": game, "error": "The submission deadline has passed. No new players can join."},
        )

    existing = (
        db.query(Player)
        .filter(Player.game_id == game.id, Player.email == email)
        .first()
    )
    if existing:
        return templates.TemplateResponse(
            request,
            "join.html",
            {"game": game, "error": "This email address has already been used to join this game. Check your email for your personal link."},
        )

    player = Player(
        game_id=game.id,
        name=name,
        email=email,
        player_token=str(uuid.uuid4()),
    )
    db.add(player)
    db.commit()

    base_url = os.getenv("BASE_URL", str(request.base_url)).rstrip("/")
    try:
        send_welcome_email(
            player=player,
            game=game,
            player_url=f"{base_url}/player/{player.player_token}",
        )
    except Exception:
        pass

    return RedirectResponse(url=f"/player/{player.player_token}", status_code=303)
