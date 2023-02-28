import os
from loguru import logger
from tinydb import TinyDB, Query
import click
import json
from dupr_client import DuprClient
from dupr_resources import Match, Team, Player
from openpyxl import Workbook
from dotenv import load_dotenv

db = TinyDB("dupr.json")
mtable = db.table('match')
ptable = db.table('player')
dupr = DuprClient()
load_dotenv()

def ppj(data):
    logger.debug(json.dumps(data, indent=4))


def save_player(data: dict) -> dict:
    """ Add play or update player in database """
    # yup pretty boring...
    # This is a very much a KLUDGE because the api
    # returns ratings in two different ways depending
    # on the player get call or the club member call
    if data.get("ratings"):
        r = data.pop("ratings")
        for (k, v) in r.items():
            data[k] = v
    q = Query()
    ids = ptable.upsert(data, q.id == int(data["id"]))
    logger.debug(f"upsert result {ids} for ID {data['id']}")
    # check ids first
    return Player().from_json(data)


@click.command()
@click.argument("pid")
def get_player(pid: int) -> dict:
    """ Load player object from database """
    q = Query()
    data = ptable.get(q.id == int(pid))
    logger.debug(data)
    player = Player().from_json(data)
    logger.debug(f"{player.id}, {player.full_name}, {player.doubles}")
    return player


def look_at_players(players: list):

    for p in players:
        save_player(p)
    print(len(players))


def dupr_add_new_player(pid: int) -> dict:
    """ Get player from DUPR if necessary """
    logger.debug(f"dupr_add_new_player for id {pid}...")
    q = Query()
    p = ptable.get(q.id == int(pid))
    if not p:
        rc, p = dupr.get_player(pid)
        logger.debug(f"dupr_add_new_player for id {pid} GET...")
        if p:
            save_player(p)
            logger.debug(f"dupr_add_new_player for id {pid} saved...")

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
@click.argument("pid")
def query_player(pid: int) -> dict:
    """ Load player from Dupr via API, good for testing """
    rc, pdata = dupr.get_player(pid)
    logger.debug(f"dupr.get_player for id {pid} GET...")
    logger.debug(pdata)
    player = Player().from_json(pdata)
    logger.debug(f"{player.id}, {player.full_name}, {player.doubles}")

    logger.info(f"Getting match history")
    dupr.get_member_match_history_p(pid)
    return player


@click.command()
def get_data():
    logger.info("Getting data from DUPR...")

    username = os.getenv("DUPR_USERNAME")
    password = os.getenv("DUPR_PASSWORD")
    dupr.auth_user(username, password)
    dupr.get_profile()

    club_id = os.getenv("DUPR_CLUB_ID")
    # dupr.get_club(club_id)
    rc, players = dupr.get_members_by_club(club_id)
    look_at_players(players)

    for p in players:
        rc, matches = dupr.get_member_match_history_p(p["id"])
        look_at_matches(matches)


@click.command()
def show_data():

    logger.info("Data stored:")
    for d in ptable:
        m = Player().from_json(d)
        # pprint.pprint(d, indent=4)
        ppj(d)
        break
        if x:
            print(x)
        print(m.match_id, m.user_id)
        for t in m.teams:
            print(t.game1, t.winner, t.player1.full_name, t.player2.full_name)

    for d in mtable:
        m = Match().from_json(d)
        # pprint.pprint(d, indent=4)
        ppj(d)
        break


def match_row(m: Match) -> tuple:
    return (m.match_id, m.user_id, m.display_identity, m.event_date, m.confirmed, m.event_format, m.match_type)


def team_row(t: Team, ratings) -> tuple:
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
    match = db.table('match')
    player = db.table('player')
    print(db.tables())
    print(len(player.all()))
    print(len(match.all()))
    #print(match.count())
    #print(player.count())

@click.command()
@click.argument("pid")
def delete_player(pid: int):
    """ Get player from DUPR if necessary """
    logger.debug(f"delete player {pid} from database")
    q = Query()
    p = ptable.get(q.id == int(pid))
    if not p:
        logger.info(f"{pid} not found")
        return
    ptable.remove(q.id == pid)


@click.command()
@click.argument("pid")
def add_player(pid: int):
    dupr_add_new_player(int(pid))


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
    cli.add_command(show_data)
    cli.add_command(write_excel)
    cli.add_command(stats)
    cli.add_command(add_player)
    cli.add_command(get_player)
    cli.add_command(delete_player)
    cli.add_command(query_player)
    cli.add_command(test_db)
    cli()
