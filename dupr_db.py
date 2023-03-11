"""
    Relational representation of DUPR Data
"""
from datetime import date
from typing import List, Optional
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy import String, ForeignKey, Integer, Float
from sqlalchemy import Table, Column, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, relationship


engine = None


def open_db():
    global engine
    # engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)
    engine = create_engine("sqlite+pysqlite:///dupr.sqlite", echo=False)
    Base.metadata.create_all(engine)
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
    if s is None:
        return None
    if s == "NR":
        return None
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
            v = f"{s_verified}" if s_verified else s  # "NR"
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
    def get(cls, sess: Session, dupr_id: int) -> "Player":
        """ Get player by id, or none
        """
        p = sess.execute(select(Player).where(
            Player.dupr_id == dupr_id)).scalar_one_or_none()
        return p

    @classmethod
    def save(this, sess: Session, player: "Player") -> "Player":
        """ Insert or update this player
            Deal with child objects
        """
        p = Player.get(sess, player.dupr_id)
        if p:
            # update, carefully
            p.full_name = player.full_name
            p.first_name = player.first_name
            p.last_name = player.last_name
            p.gender = player.gender
            p.age = player.age
            p.image_url = player.image_url
            p.email = player.email
            p.phone = player.phone

            p.rating.doubles = player.rating.doubles if player.rating.doubles else None
            p.rating.doubles_verified = player.rating.doubles_verified if player.rating.doubles_verified else None
            p.rating.is_doubles_provisional = player.rating.is_doubles_provisional

            p.rating.singles = player.rating.singles if player.rating.singles else None
            p.rating.singles_verified = player.rating.singles_verified if player.rating.singles_verified else None
            p.rating.is_singles_provisional = player.rating.is_singles_provisional
            sess.add(p)
            return p
        else:
            sess.add(player)
            return player

    @classmethod
    def from_json(cls, d: dict) -> 'Player':
        try:
            p = Player()
            # this can be duprId or id
            p.dupr_id = d.get("duprId")
            if not p.dupr_id:
                p.dupr_id = d.get("id")
            # There seems to a API bug where player in matches
            # return a different DuprID in the form of NNNANNN where as
            # other IDs are just numeric. So stick to id field
            p.dupr_id = d.get("id")
            p.full_name = d.get("fullName")
            p.image_url = d.get("imageUrl")

            p.email = d.get("email")
            p.gender = d.get("gender")
            p.age = d.get("age")

            p.rating = Rating()

            _fix_rating_json(d)
            p.rating.singles = _cv_rating_json(d.get("singles"))
            p.rating.singles_verified = _cv_rating_json(d.get("singlesVerified"))
            p.rating.is_singles_provisional = d.get("singlesProvisional")

            p.rating.doubles = _cv_rating_json(d.get("doubles"))
            p.rating.doubles_verified = _cv_rating_json(d.get("doublesVerified"))
            p.rating.is_doubles_provisional = d.get("doublesProvisional")
            return p
        except:
            logger.exception(d)
            raise


class Match(Base):
    __tablename__ = "match"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column()
    name: Mapped[str] = mapped_column(String(246))
    date: Mapped[str] = mapped_column(String(16))
    teams: Mapped[List["MatchTeam"]] = relationship(back_populates="match")
    match_type: Mapped[str] = mapped_column(default="")
    match_source: Mapped[str] = mapped_column(default="")
    match_score_added: Mapped[bool] = mapped_column(default=True)

    def __repr__(self) -> str:
        return f"Match {self.name} on {self.date}"

    @classmethod
    def get_by_id(cls, sess: Session, match_id: int) -> "Match":
        m = sess.execute(select(Match).where(
            Match.match_id == match_id)).scalar_one_or_none()
        return m

    @classmethod
    def from_json(cls, d: dict):

        try:
            m = Match()
            m.match_id = d.get("matchId")
            m.user_id = d.get("userId")
            m.display_identity = d.get("displayIdentity")
            m.confirmed = d.get("confirmed")
            m.date = date.fromisoformat(d.get("eventDate"))
            # need to try different fields...
            m.name = d.get("eventName")
            if not m.name:
                m.name = d.get("league")
            if not m.name:
                m.name = d.get("tournament", "")
            m.event_format = d.get("eventFormat")
            m.match_score_added = d.get("matchScoreAdded")
            m.match_source = d.get("matchSource")
            m.match_type = d.get("matchType")

            for jt in d.get("teams"):
                t = MatchTeam().from_json(jt)
                m.teams.append(t)
            return m

        except:
            logger.exception(d)
            raise


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

    @classmethod
    def from_json(cls, d: dict):

        try:
            mt = MatchTeam()
            mt.score1 = d.get("game1")
            mt.score2 = d.get("game2")
            mt.score3 = d.get("game3")
            p = Player().from_json(d.get("player1"))
            mt.players.append(p)
            pdata = d.get("player2")
            if pdata:
                p2 = Player().from_json(pdata)
                mt.players.append(p2)
            mt.is_winner = d.get("winner")
            return mt

        except:
            logger.exception(d)
            raise


class MatchDetail(Base):
    """
    A denormalized table for match and players because this is the primary
    query that is useful.
    """

    __tablename__ = "match_detail"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("match.id"))
    match: Mapped["Match"] = relationship()
    # team 1 is the winning team
    team_1_score: Mapped[int] = mapped_column()
    team_2_score: Mapped[int] = mapped_column()

    team_1_player_1_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    team_1_player_2_id: Mapped[Optional[int]] = mapped_column(ForeignKey("player.id"))
    team_2_player_1_id: Mapped[int] = mapped_column(ForeignKey("player.id"))
    team_2_player_2_id: Mapped[Optional[int]] = mapped_column(ForeignKey("player.id"))

    def __repr__(self) -> str:
        return f"Match {self.name} on {self.date}"

    @classmethod
    def get_by_id(cls, sess: Session, match_id: int) -> "Match":
        m = sess.execute(select(Match).where(
            Match.match_id == match_id)).scalar_one_or_none()
        return m
