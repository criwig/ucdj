from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    admin_token = Column(String, unique=True, index=True, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    # collecting | guessing | ended
    state = Column(String, default="collecting", nullable=False)
    submission_deadline = Column(DateTime, nullable=True)
    guessing_deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    players = relationship("Player", back_populates="game", order_by="Player.joined_at")
    slots = relationship("Slot", back_populates="game", order_by="Slot.order")
    submissions = relationship("Submission", back_populates="game")


class Slot(Base):
    """A named category defined by the admin (e.g. 'Best pump-up song', 'Favourite film')."""

    __tablename__ = "slots"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    name = Column(String, nullable=False)
    order = Column(Integer, default=0)

    game = relationship("Game", back_populates="slots")
    fields = relationship("SlotField", back_populates="slot", order_by="SlotField.order")
    submissions = relationship("Submission", back_populates="slot")


class SlotField(Base):
    """A named input field within a slot (e.g. 'Artist', 'Spotify URL', 'Why you love it')."""

    __tablename__ = "slot_fields"

    id = Column(Integer, primary_key=True)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)
    name = Column(String, nullable=False)
    field_type = Column(String, default="text")   # text | url
    required = Column(Boolean, default=True)
    order = Column(Integer, default=0)

    slot = relationship("Slot", back_populates="fields")
    values = relationship("SubmissionValue", back_populates="field")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    player_token = Column(String, unique=True, index=True, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    game = relationship("Game", back_populates="players")
    submissions = relationship(
        "Submission", foreign_keys="Submission.submitted_by_id", back_populates="submitted_by"
    )
    assigned_submissions = relationship(
        "Submission", foreign_keys="Submission.assigned_to_id", back_populates="assigned_to"
    )
    guesses_made = relationship(
        "Guess", foreign_keys="Guess.guesser_id", back_populates="guesser"
    )


class Submission(Base):
    """One entry per player per slot. Contains SubmissionValues for each SlotField."""

    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)
    submitted_by_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    game = relationship("Game", back_populates="submissions")
    slot = relationship("Slot", back_populates="submissions")
    submitted_by = relationship(
        "Player", foreign_keys=[submitted_by_id], back_populates="submissions"
    )
    assigned_to = relationship(
        "Player", foreign_keys=[assigned_to_id], back_populates="assigned_submissions"
    )
    values = relationship("SubmissionValue", back_populates="submission",
                          order_by="SubmissionValue.field_id")
    guesses = relationship("Guess", back_populates="submission")

    def display_values(self):
        """Returns list of (field_name, value) pairs for display."""
        return [(v.field.name, v.value) for v in self.values if v.value]


class SubmissionValue(Base):
    """The value a player entered for one field of one submission."""

    __tablename__ = "submission_values"

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("slot_fields.id"), nullable=False)
    value = Column(String, default="")

    submission = relationship("Submission", back_populates="values")
    field = relationship("SlotField", back_populates="values")


class Guess(Base):
    __tablename__ = "guesses"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    guesser_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    guessed_player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    guesser = relationship(
        "Player", foreign_keys=[guesser_id], back_populates="guesses_made"
    )
    submission = relationship("Submission", back_populates="guesses")
    guessed_player = relationship("Player", foreign_keys=[guessed_player_id])

    __table_args__ = (
        UniqueConstraint("guesser_id", "submission_id", name="uq_guesser_submission"),
    )
