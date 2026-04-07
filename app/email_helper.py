import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _send(to_email: str, to_name: str, subject: str, text: str, html: str) -> None:
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    use_ssl = os.getenv("SMTP_SSL", "false").lower() == "true"
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")
    from_addr = os.getenv("SMTP_FROM", user)

    if not host or not user:
        return  # Email not configured — skip silently

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = f"{to_name} <{to_email}>"
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    ctx = ssl.create_default_context()
    if use_ssl:
        with smtplib.SMTP_SSL(host, port, context=ctx) as server:
            server.login(user, password)
            server.sendmail(from_addr, to_email, msg.as_string())
    else:
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(user, password)
            server.sendmail(from_addr, to_email, msg.as_string())


def send_welcome_email(player, game, player_url: str) -> None:
    slot_lines_text = "\n".join(
        f"  • {s.name} ({', '.join(f.name for f in s.fields)})"
        for s in game.slots
    )
    slot_lines_html = "".join(
        f"<li><strong>{s.name}</strong> — {', '.join(f.name for f in s.fields)}</li>"
        for s in game.slots
    )

    text = f"""Hi {player.name},

You've joined "{game.title}"!

You need to submit one entry per category:
{slot_lines_text}

Your personal page (submit entries + later make guesses):
{player_url}

Bookmark this link — it's your access to the whole game.
"""
    html = f"""<p>Hi {player.name},</p>
<p>You've joined <strong>{game.title}</strong>!</p>
<p>You need to submit one entry per category:</p>
<ul>{slot_lines_html}</ul>
<p><a href="{player_url}">Open your personal page</a> to submit your entries and later make your guesses.</p>
<p><em>Bookmark this link — it's your access to the whole game.</em></p>"""

    _send(
        player.email,
        player.name,
        f"You joined {game.title} — submit your entries!",
        text,
        html,
    )


def send_distribution_email(player, game, player_url: str) -> None:
    count = len(player.assigned_submissions)

    text = f"""Hi {player.name},

The guessing phase for "{game.title}" has started!

You've been assigned {count} submission(s) to identify.
Open your page to start guessing: {player_url}

You can update your guesses at any time until the admin ends the game.
"""
    html = f"""<p>Hi {player.name},</p>
<p>The guessing phase for <strong>{game.title}</strong> has started!</p>
<p>You've been assigned <strong>{count} submission(s)</strong> to identify.</p>
<p><a href="{player_url}"><strong>Open your page to start guessing</strong></a></p>
<p><em>You can update your guesses at any time until the admin ends the game.</em></p>"""

    _send(
        player.email,
        player.name,
        f"Time to guess — {game.title} is live!",
        text,
        html,
    )
