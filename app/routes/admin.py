import os
import random

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..email_helper import send_distribution_email
from ..models import Game, Guess, Submission

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/admin/{admin_token}", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request, admin_token: str, db: Session = Depends(get_db)
):
    game = db.query(Game).filter(Game.admin_token == admin_token).first()
    if not game:
        raise HTTPException(status_code=404, detail="Admin page not found")

    base_url = os.getenv("BASE_URL", str(request.base_url)).rstrip("/")
    join_url = f"{base_url}/game/{game.slug}/join"
    admin_url = f"{base_url}/admin/{admin_token}"

    players_status = []
    for player in game.players:
        submitted_slot_ids = {s.slot_id for s in player.submissions}
        total = len(game.slots)
        submitted = len(submitted_slot_ids)
        players_status.append(
            {
                "player": player,
                "submitted": submitted,
                "total": total,
                "complete": submitted == total,
            }
        )

    all_complete = all(p["complete"] for p in players_status) if players_status else False

    results = _calculate_results(game) if game.state == "ended" else None

    guessing_progress = None
    if game.state == "guessing":
        total_assigned = sum(1 for s in game.submissions if s.assigned_to_id)
        total_guesses = db.query(Guess).filter(Guess.game_id == game.id).count()
        guessing_progress = {"assigned": total_assigned, "guessed": total_guesses}

    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "game": game,
            "admin_url": admin_url,
            "join_url": join_url,
            "players_status": players_status,
            "all_complete": all_complete,
            "results": results,
            "guessing_progress": guessing_progress,
        },
    )


@router.post("/admin/{admin_token}/distribute")
async def distribute(
    request: Request, admin_token: str, db: Session = Depends(get_db)
):
    game = db.query(Game).filter(Game.admin_token == admin_token).first()
    if not game or game.state != "collecting":
        raise HTTPException(status_code=400, detail="Cannot distribute at this time")

    # For each slot, cyclic derangement so no one gets their own submission back
    for slot in game.slots:
        subs = (
            db.query(Submission)
            .filter(Submission.game_id == game.id, Submission.slot_id == slot.id)
            .all()
        )
        if len(subs) < 2:
            continue

        random.shuffle(subs)
        for i, sub in enumerate(subs):
            sub.assigned_to_id = subs[(i + 1) % len(subs)].submitted_by_id

    game.state = "guessing"
    db.commit()
    db.refresh(game)

    base_url = os.getenv("BASE_URL", str(request.base_url)).rstrip("/")
    for player in game.players:
        if player.assigned_submissions:
            try:
                send_distribution_email(
                    player=player,
                    game=game,
                    player_url=f"{base_url}/player/{player.player_token}",
                )
            except Exception:
                pass

    return RedirectResponse(url=f"/admin/{admin_token}", status_code=303)


@router.post("/admin/{admin_token}/end")
async def end_game(admin_token: str, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.admin_token == admin_token).first()
    if not game or game.state != "guessing":
        raise HTTPException(status_code=400, detail="Cannot end game at this time")

    game.state = "ended"
    db.commit()
    return RedirectResponse(url=f"/admin/{admin_token}", status_code=303)


def _calculate_results(game):
    # Leaderboard — sorted by score descending
    leaderboard = []
    for player in game.players:
        correct = sum(
            1
            for g in player.guesses_made
            if g.guessed_player_id == g.submission.submitted_by_id
        )
        leaderboard.append(
            {
                "player": player,
                "correct": correct,
                "total": len(player.guesses_made),
            }
        )
    leaderboard.sort(key=lambda x: x["correct"], reverse=True)

    # Breakdown grouped by guesser (player who received and guessed each submission)
    by_player = []
    for player in game.players:
        entries = []
        for sub in sorted(player.assigned_submissions, key=lambda s: s.slot.order):
            guess = next(
                (g for g in sub.guesses if g.guesser_id == player.id), None
            )
            entries.append(
                {
                    "submission": sub,
                    "guess": guess,
                    "correct": guess is not None
                    and guess.guessed_player_id == sub.submitted_by_id,
                }
            )
        if entries:
            correct_count = sum(1 for e in entries if e["correct"])
            by_player.append(
                {"player": player, "entries": entries, "correct": correct_count}
            )
    # Same order as leaderboard
    by_player.sort(key=lambda x: x["correct"], reverse=True)

    return {"leaderboard": leaderboard, "by_player": by_player}
