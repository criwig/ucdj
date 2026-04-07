import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Guess, Player, Submission, SubmissionValue

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/player/{player_token}", response_class=HTMLResponse)
async def player_page(
    request: Request, player_token: str, db: Session = Depends(get_db)
):
    player = db.query(Player).filter(Player.player_token == player_token).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    game = player.game
    base_url = os.getenv("BASE_URL", str(request.base_url)).rstrip("/")
    player_url = f"{base_url}/player/{player.player_token}"
    context: dict = {"player": player, "game": game, "player_url": player_url}

    if game.state == "collecting":
        existing_subs = {s.slot_id: s for s in player.submissions}
        context["existing"] = existing_subs
        context["slots"] = game.slots
        timestamps = [s.submitted_at for s in player.submissions if s.submitted_at]
        context["last_saved_at"] = max(timestamps) if timestamps else None

    else:  # guessing or ended
        context["my_submissions"] = sorted(
            player.submissions, key=lambda s: s.slot.order
        )

        existing_guesses = {g.submission_id: g for g in player.guesses_made}
        assigned = sorted(player.assigned_submissions, key=lambda s: s.slot.order)

        context["assigned"] = [
            {
                "submission": s,
                "existing_guess": existing_guesses.get(s.id),
                "correct": (
                    existing_guesses.get(s.id) is not None
                    and existing_guesses[s.id].guessed_player_id == s.submitted_by_id
                )
                if game.state == "ended"
                else None,
            }
            for s in assigned
        ]

        guess_timestamps = [g.submitted_at for g in player.guesses_made if g.submitted_at]
        context["last_guessed_at"] = max(guess_timestamps) if guess_timestamps else None
        context["other_players"] = [p for p in game.players if p.id != player.id]

        if game.state == "ended":
            context["score"] = sum(1 for e in context["assigned"] if e["correct"])

    return templates.TemplateResponse(request, "player.html", context)


@router.post("/player/{player_token}/submit")
async def submit(request: Request, player_token: str, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.player_token == player_token).first()
    if not player:
        raise HTTPException(status_code=404)
    game = player.game
    if game.state != "collecting":
        raise HTTPException(status_code=400, detail="Submission is closed")
    if game.submission_deadline and datetime.now() > game.submission_deadline:
        base_url = os.getenv("BASE_URL", str(request.base_url)).rstrip("/")
        return templates.TemplateResponse(
            request, "deadline.html",
            {
                "player": player,
                "game": game,
                "player_url": f"{base_url}/player/{player.player_token}",
                "deadline": game.submission_deadline,
                "mode": "submit",
            },
            status_code=403,
        )

    form = await request.form()

    # Validate all required fields across all slots before saving anything
    errors = []
    for slot in game.slots:
        for field in slot.fields:
            if field.required:
                val = (form.get(f"field_{field.id}") or "").strip()
                if not val:
                    errors.append(f'"{slot.name}" — {field.name} is required.')

    if errors:
        existing_subs = {s.slot_id: s for s in player.submissions}
        timestamps = [s.submitted_at for s in player.submissions if s.submitted_at]
        base_url = os.getenv("BASE_URL", str(request.base_url)).rstrip("/")
        return templates.TemplateResponse(
            request,
            "player.html",
            {
                "player": player,
                "game": game,
                "player_url": f"{base_url}/player/{player.player_token}",
                "existing": existing_subs,
                "slots": game.slots,
                "last_saved_at": max(timestamps) if timestamps else None,
                "errors": errors,
            },
        )

    for slot in game.slots:
        sub = (
            db.query(Submission)
            .filter(
                Submission.submitted_by_id == player.id,
                Submission.slot_id == slot.id,
            )
            .first()
        )

        field_values = {
            field.id: (form.get(f"field_{field.id}") or "").strip()
            for field in slot.fields
        }

        if not sub:
            sub = Submission(
                game_id=game.id,
                slot_id=slot.id,
                submitted_by_id=player.id,
            )
            db.add(sub)
            db.flush()

        existing_values = {sv.field_id: sv for sv in sub.values}
        for field_id, val in field_values.items():
            if field_id in existing_values:
                existing_values[field_id].value = val
            else:
                db.add(SubmissionValue(
                    submission_id=sub.id,
                    field_id=field_id,
                    value=val,
                ))

    db.commit()
    return RedirectResponse(url=f"/player/{player_token}/submitted", status_code=303)


@router.get("/player/{player_token}/submitted", response_class=HTMLResponse)
async def submitted_success(
    request: Request, player_token: str, db: Session = Depends(get_db)
):
    player = db.query(Player).filter(Player.player_token == player_token).first()
    if not player:
        raise HTTPException(status_code=404)
    base_url = os.getenv("BASE_URL", str(request.base_url)).rstrip("/")
    player_url = f"{base_url}/player/{player.player_token}"
    return templates.TemplateResponse(
        request,
        "success.html",
        {
            "player": player,
            "game": player.game,
            "player_url": player_url,
            "mode": "submitted",
        },
    )


@router.post("/player/{player_token}/guesses")
async def submit_guesses(
    request: Request, player_token: str, db: Session = Depends(get_db)
):
    player = db.query(Player).filter(Player.player_token == player_token).first()
    if not player:
        raise HTTPException(status_code=404)
    if player.game.state != "guessing":
        raise HTTPException(status_code=400, detail="Guessing is closed")
    if player.game.guessing_deadline and datetime.now() > player.game.guessing_deadline:
        base_url = os.getenv("BASE_URL", str(request.base_url)).rstrip("/")
        return templates.TemplateResponse(
            request, "deadline.html",
            {
                "player": player,
                "game": player.game,
                "player_url": f"{base_url}/player/{player.player_token}",
                "deadline": player.game.guessing_deadline,
                "mode": "guess",
            },
            status_code=403,
        )

    form = await request.form()
    game = player.game

    # Validate all assigned submissions have a guess
    missing = [
        sub for sub in player.assigned_submissions
        if not (form.get(f"guess_{sub.id}", "") or "").strip()
    ]
    if missing:
        existing_guesses = {g.submission_id: g for g in player.guesses_made}
        assigned = sorted(player.assigned_submissions, key=lambda s: s.slot.order)
        guess_timestamps = [g.submitted_at for g in player.guesses_made if g.submitted_at]
        base_url = os.getenv("BASE_URL", str(request.base_url)).rstrip("/")
        return templates.TemplateResponse(
            request,
            "player.html",
            {
                "player": player,
                "game": game,
                "player_url": f"{base_url}/player/{player.player_token}",
                "my_submissions": sorted(player.submissions, key=lambda s: s.slot.order),
                "assigned": [
                    {
                        "submission": s,
                        "existing_guess": existing_guesses.get(s.id),
                        "correct": None,
                    }
                    for s in assigned
                ],
                "last_guessed_at": max(guess_timestamps) if guess_timestamps else None,
                "other_players": [p for p in game.players if p.id != player.id],
                "errors": [f'Please guess who submitted "{sub.slot.name}."' for sub in missing],
            },
        )

    for sub in player.assigned_submissions:
        raw = form.get(f"guess_{sub.id}", "")
        try:
            guessed_player_id = int(raw)
        except ValueError:
            continue

        existing = (
            db.query(Guess)
            .filter(Guess.guesser_id == player.id, Guess.submission_id == sub.id)
            .first()
        )
        if existing:
            existing.guessed_player_id = guessed_player_id
        else:
            db.add(
                Guess(
                    game_id=player.game_id,
                    guesser_id=player.id,
                    submission_id=sub.id,
                    guessed_player_id=guessed_player_id,
                )
            )

    db.commit()
    return RedirectResponse(url=f"/player/{player_token}/guessed", status_code=303)


@router.get("/player/{player_token}/guessed", response_class=HTMLResponse)
async def guessed_success(
    request: Request, player_token: str, db: Session = Depends(get_db)
):
    player = db.query(Player).filter(Player.player_token == player_token).first()
    if not player:
        raise HTTPException(status_code=404)
    base_url = os.getenv("BASE_URL", str(request.base_url)).rstrip("/")
    player_url = f"{base_url}/player/{player.player_token}"
    return templates.TemplateResponse(
        request,
        "success.html",
        {
            "player": player,
            "game": player.game,
            "player_url": player_url,
            "mode": "guessed",
        },
    )
