"""
    Relational representation of DUPR Data
"""
from datetime import date
from operator import attrgetter
from typing import List, Optional
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy import String, ForeignKey, Integer, Float
from sqlalchemy import Table, Column
from sqlalchemy.orm import Session
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, relationship


engine = None


def open_db():
    global engine
    engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)
    engine = create_engine("sqlite+pysqlite:///dupr.sqlite", echo=False)
    return engine


class Base(DeclarativeBase):
    pass


def _fix_rating_json(data: dict) -> dict:
    # This is a very much a KLUDGE because the api
    # returns ratings in two different ways depending
    # on the player get call or the club member call
    if data.get("ratings"):
        r = data.pop("ratings")
        for (k, v) in r.items():
            data[k] = v
    return data


def _cv_rating_json(s: str):
    # deal with NR vs 3.45
    if s == "NR": return None
    return float(s)


class Rating(Base):
    __tablename__ = "rating"

    id: Mapped[int] = mapped_column(primary_key=True)
    doubles: Mapped[Optional[float]] = mapped_column(Float)
    doubles_verified: Mapped[Optional[float]] = mapped_column(Float)
    is_doubles_provisional: Mapped[bool] = mapped_column(default=True)

    singles: Mapped[Optional[float]] = mapped_column(Float)
    singles_verified: Mapped[Optional[float]] = mapped_column(Float)
    is_singles_provisional: Mapped[bool] = mapped_column(default=True)

    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    player: Mapped["Player"] = relationship(back_populates="rating")

    @staticmethod
    def str_rating(s, s_verified, is_provisional):
        if is_provisional:
            v = f"{s}*" if s else "NR"
            return v
        else:
            v = f"{s_verified}" if s_verified else s # "NR"
            return v

    def singles_rating(self):
        return Rating.str_rating(
            self.singles, self.singles_verified,
            self.is_singles_provisional)

    def doubles_rating(self):
        return Rating.str_rating(
            self.doubles, self.doubles_verified,
            self.is_doubles_provisional)

    def __repr__(self) -> str:
        return f"{self.doubles_rating()} / {self.singles_rating()}"


class Player(Base):
    __tablename__ = "player"

    id: Mapped[int] = mapped_column(primary_key=True)
    dupr_id: Mapped[int] = mapped_column(Integer)
    full_name: Mapped[str] = mapped_column(String(128))
    first_name: Mapped[Optional[str]] = mapped_column(String(128))
    last_name: Mapped[Optional[str]] = mapped_column(String(128))
    gender: Mapped[Optional[str]] = mapped_column()
    age: Mapped[Optional[int]] = mapped_column()
    image_url: Mapped[Optional[str]] = mapped_column(String(256))
    email: Mapped[Optional[str]] = mapped_column(String(256))
    phone: Mapped[Optional[str]] = mapped_column(String(64))

    # Note: in 1-1 mapping, no need to use the uselist=false
    # param if we are using Mapped annotation
    rating: Mapped["Rating"] = relationship(back_populates="player")

    match_teams: Mapped[List["MatchTeam"]] = relationship(
        secondary="match_team_player"
    )

    def __repr__(self) -> str:
        return f"Player {self.full_name} {self.rating}"

    @classmethod
    def from_json(cls, d: dict) -> 'Player':
        try:
            p = Player()
            # this can be duprId or id
            p.dupr_id = d.get("duprId")
            if not p.dupr_id:
                p.dupr_id = d.get("id")
            p.full_name = d.get("fullName")
            p.image_url = d.get("imageUrl")

            p.email = d.get("email")
            p.gender = d.get("gender")
            p.age = d.get("age")

            p.rating = Rating()

            _fix_rating_json(d)
            p.rating.singles = _cv_rating_json(d.get("singles"))
            p.rating.singlesVerified = _cv_rating_json(d.get("singlesVerified"))
            p.rating.singlesProvisional = d.get("singlesProvisional")

            p.rating.doubles = _cv_rating_json(d.get("doubles"))
            p.rating.doublesVerified = _cv_rating_json(d.get("doublesVerified"))
            p.rating.doublesProvisional = d.get("doublesProvisional")
            return p
        except:
            logger.exception(d)
            raise


class Match(Base):
    __tablename__ = "match"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(246))
    date: Mapped[str] = mapped_column(String(16))
    teams: Mapped[List["MatchTeam"]] = relationship(back_populates="match")

    def __repr__(self) -> str:
        return f"Match {self.name} on {self.date}"


match_team_player = Table(
    "match_team_player",
    Base.metadata,
    Column("match_team_id", ForeignKey("match_team.id")),
    Column("player_id", ForeignKey("player.id"))
)


class MatchTeam(Base):
    __tablename__ = "match_team"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id = mapped_column(ForeignKey("match.id"))
    match: Mapped[Match] = relationship(back_populates="teams")
    score1: Mapped[int] = mapped_column()
    score2: Mapped[Optional[int]] = mapped_column()
    score3: Mapped[Optional[int]] = mapped_column()
    is_winner: Mapped[bool] = mapped_column()
    players: Mapped[List["Player"]] = relationship(
        secondary=match_team_player,
        back_populates="match_teams"
        )

    def __repr__(self) -> str:
        ps = ",".join([p.full_name for p in self.players])
        return f"Match Team {ps}"




class Teamx:
    def __init__(self):
        self.game_score1 = -1
        self.game_score2 = -1
        self.game_score3 = -1
        self.winner = False
        self.player1 = None
        self.player2 = None

    def from_json(self, d: dict) -> 'Team':
        try:
            self.game_score1 = d.get("game1")
            self.game_score2 = d.get("game2")
            self.game_score3 = d.get("game3")
            self.player1 = Player().from_json(d.get("player1"))
            p2 = d.get("player2")
            if p2:
                self.player2 = Player().from_json(d.get("player2"))
            self.winner = d.get("winner")
            return self
        except:
            logger.exception(d)
            print(d)
            raise


class Matchx:
    def __init__(self):
        self.id = 0
        self.match_id = 0
        self.user_id = 0
        self.display_identity = ""
        self.event_date = None
        self.confirmed = False
        self.event_format = ""
        self.match_score_added = False
        self.match_source = None  # dupr, manual, league
        self.match_type = None  # side_only vs rally

        self.teams = []

    def team1(self):
        if self.teams[0]:
            return self.teams[0]

    def team2(self):
        if self.teams[1]:
            return self.teams[1]

    def is_double(self):
        return self.event_format == "DOUBLES"  # not "SINGLES"

    def __repr__(self):
        t = self.team1()
        s = f"player1: {t.player1}"
        return s

    def from_json(self, d: dict) -> 'Match':
        self.match_id = d.get("matchId")
        self.user_id = d.get("userId")
        self.display_identity = d.get("displayIdentity")
        self.confirmed = d.get("confirmed")
        self.event_date = date.fromisoformat(d.get("eventDate"))
        self.event_format = d.get("eventFormat")
        self.match_score_added = d.get("matchScoreAdded")        
        self.match_source = d.get("matchSource")
        self.match_type = d.get("matchType")        

        for jt in d.get("teams"):
            t = Team().from_json(jt)
            self.teams.append(t)
        return self