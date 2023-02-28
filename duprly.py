import os
from loguru import logger
import click
import json
from dupr_client import DuprClient
from openpyxl import Workbook
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session
from dupr_db import open_db, Base, Player, Match, MatchTeam, Rating

load_dotenv()
dupr = DuprClient()

eng = open_db()
with Session(eng) as sess:
    Base.metadata.create_all(eng)


def ppj(data):
    logger.debug(json.dumps(data, indent=4))


def dupr_auth():
    username = os.getenv("DUPR_USERNAME")
    password = os.getenv("DUPR_PASSWORD")
    dupr.auth_user(username, password)


@click.command()
def get_all_players():
    dupr_auth()

    club_id = os.getenv("DUPR_CLUB_ID")
    rc, players = dupr.get_members_by_club(club_id)
    for pdata in players:
        # rc, matches = dupr.get_member_match_history_p(p["id"])
        # look_at_matches(matches)
        with Session(eng) as sess:
            player = Player().from_json(pdata)
            logger.debug(f"{player.id}, {player.full_name}, {player.rating}")

            p = sess.execute(select(Player).where(
                Player.dupr_id==player.dupr_id)).scalar_one_or_none()
            if p:
                # update
                p.from_json(pdata)
                player = p

            sess.add_all([player, ])
            sess.commit()


@click.command()
@click.argument("pid")
def get_player(pid: int) -> Player:
    """ Get player from DUPR by ID """
    dupr_auth()

    rc, pdata = dupr.get_player(pid)
    logger.debug(f"dupr.get_player for id {pid} GET...")
    logger.debug(pdata)

    with Session(eng) as sess:

        player = Player().from_json(pdata)
        logger.debug(f"{player.dupr_id}, {player.full_name}, {player.rating}")

        p = sess.execute(select(Player).where(
                Player.dupr_id==player.dupr_id)).scalar_one_or_none()
        if p:
            # update
            p.from_json(pdata)
            player = p

        sess.add_all([player, ])
        sess.commit()

    # logger.info(f"Getting match history")
    # dupr.get_member_match_history_p(pid)
    return player


def look_at_matches(matches: list):

    q = Query()
    for m in matches:
        print(m)
        print(m["matchId"])
        print(type(m["matchId"]))
        mtable.upsert(m, q.matchId == int(m["matchId"]))

        # do we need to pull player data?
        match = Match().from_json(m)
        dupr_add_new_player(match.team1().player1.id)
        dupr_add_new_player(match.team2().player1.id)
        if match.is_double():
            dupr_add_new_player(match.team1().player2.id)
            dupr_add_new_player(match.team2().player2.id)

    print(len(matches))



@click.command()
def get_data():
    """ Update all data """
    logger.info("Getting data from DUPR...")

    get_all_players()
    players = []
    for p in players:
        rc, matches = dupr.get_member_match_history_p(p["id"])
        look_at_matches(matches)


def match_row(m: Match) -> tuple:
    return (m.match_id, m.user_id, m.display_identity, m.event_date, m.confirmed, m.event_format, m.match_type)


def team_row(t: MatchTeam, ratings) -> tuple:
    doubles1 = ratings.get(t.player1.id, ("NA", "NA", "NA"))[2]
    if t.player2:
        doubles2 = ratings.get(t.player2.id, ("NA", "NA", "NA"))[2]
        p2_row = (t.player2.dupr_id, t.player2.full_name, doubles2)
    else:
        doubles2 = "NA"
        p2_row = ("", "", "NA")

    return (t.player1.dupr_id, t.player1.full_name, doubles1) + p2_row + (t.game_score1,)


@click.command()
def write_excel():
    from openpyxl.styles import numbers

    wb = Workbook()
    ws = wb.active
    ws.title = "players"
    # cache all ratings
    player_ratings = {}

    ws.append(("id", "DUPR id", "full name", "gender", "age") +
                ("single", "single verified", "single provisional") +
                ("double", "double verified", "double provisional")
            )

    for d in ptable:
        p = Player().from_json(d)
        ws.append((p.id, p.dupr_id, p.full_name, p.gender, p.age,
        p.singles, p.singles_verified, p.singles_provisional,
        p.doubles, p.doubles_verified, p.doubles_provisional))
        player_ratings[p.id] = (p.singles, p.singles_verified, p.doubles, p.doubles_verified)

    col = ws.column_dimensions['A']
    col.number_format = u'#,##0'

    ws = wb.create_sheet("matches")

    prow = ("player1 DUPR ID", "player 1", "player1 doubles",
            "player2 DUPR ID", "player 2", "player2 doubles",
            "score1")
    ws.append(("match id", "user_id", "match display", "event date", "confirmed", "format", "match type") +
            prow + prow)
    for d in mtable:
        m = Match().from_json(d)
        t1 = m.teams[0]
        t2 = m.teams[1]
        ws.append((match_row(m) + team_row(m.teams[0], player_ratings) +
                    team_row(m.teams[1], player_ratings)))


    col = ws.column_dimensions['A']
    col.number_format = u'#,##0'
    col = ws.column_dimensions['B']
    col.number_format = u'#,##0'
    col = ws.column_dimensions['J']
    col.format = numbers.FORMAT_TEXT

    wb.save(filename="dupr.xlsx")


@click.command()
def stats():
    with Session(eng) as sess:
        c = sess.query(Player).count()
        print(f"number of players {c}")
        c = sess.query(Match).count()
        print(f"number of matches {c}")


@click.command()
@click.argument("pid")
def get_player(pid: int) -> Player:
    """ Get player from DUPR by ID """
    dupr_auth()

    rc, pdata = dupr.get_player(pid)
    logger.debug(f"dupr.get_player for id {pid} GET...")
    logger.debug(pdata)

    with Session(eng) as sess:

        player = Player().from_json(pdata)
        logger.debug(f"{player.dupr_id}, {player.full_name}, {player.rating}")

        p = sess.execute(select(Player).where(
                Player.dupr_id==player.dupr_id)).scalar_one_or_none()
        if p:
            # update
            p.from_json(pdata)
            player = p

        sess.add_all([player,])
        sess.commit()

    # logger.info(f"Getting match history")
    # dupr.get_member_match_history_p(pid)
    return player


@click.command()
@click.argument("pid")
def delete_player(pid: int):
    """ Get player from DUPR if necessary """
    logger.debug(f"delete player {pid} from database")
    pass


@click.command()
def test_db():
    from dupr_db import open_db, Base, Player, Match, MatchTeam

    e = open_db()
    with Session(e) as sess:
        Base.metadata.create_all(e)

        print(type(Player))
        p = Player(dupr_id=123, full_name="Mr Smith")


@click.group()
def cli():
    pass


if __name__ == "__main__":
    logger.add("duprly_{time}.log")
    cli.add_command(get_data)
    cli.add_command(write_excel)
    cli.add_command(stats)
    cli.add_command(get_player)
    cli.add_command(delete_player)
    cli.add_command(test_db)
    cli()
