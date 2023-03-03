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


def get_player_from_dupr(pid: int) -> Player:

    rc, pdata = dupr.get_player(pid)
    logger.debug(f"dupr.get_player for id {pid} GET...")
    ppj(pdata)

    player = None

    with Session(eng) as sess:
        player = Player().from_json(pdata)
        logger.debug(f"{player.dupr_id}, {player.full_name}, {player.rating}")
        Player.save(sess, player)
        sess.commit()

    return player


def get_all_players_from_dupr():
    club_id = os.getenv("DUPR_CLUB_ID")
    _rc, players = dupr.get_members_by_club(club_id)
    for pdata in players:
        with Session(eng) as sess:
            player = Player().from_json(pdata)
            logger.debug(f"{player.id}, {player.full_name}, {player.rating}")
            Player.save(sess, player)
            sess.commit()


def get_matches_from_dupr(dupr_id: int):
    """ Get match history for specified player """

    _rc, matches = dupr.get_member_match_history_p(dupr_id)

    with Session(eng) as sess:

        for mdata in matches:
            print("match")
            ppj(mdata)
            m = Match().from_json(mdata)
            # now we have match, and potentially four new players
            # deal with the fact that player may already exists
            m1 = Match.get_by_id(sess, m.match_id)
            if m1:
                # update
                continue  # skip

            for team in m.teams:
                print(f"team {team}")
                plist = []
                for p in team.players:
                    # This is very kludgy, the player data returned from the MatchHistory
                    # call only has a few fields
                    p1 = sess.execute(select(Player).where(
                        Player.dupr_id == p.dupr_id)).scalar_one_or_none()
                    if p1:
                        # set team to this player object instead
                        plist.append(p1)
                        print(f"use existing populated player")
                    else:
                        plist.append(p)
                        print(f"saved new limited data player")
                team.players = plist
            sess.add(m)
            sess.commit()


def update_ratings_from_dupr():

    with Session(eng) as sess:
        # Has to use "has" not "any" because it is 1=1? Also need to have something
        # in the has() function
        dupr_ids = sess.scalars(select(Player.dupr_id).where(
            ~Player.rating.has(Rating.doubles)))

    for i in dupr_ids:
        get_player_from_dupr(i)


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
        ws.append((
            p.id, p.dupr_id, p.full_name, p.gender, p.age,
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
def get_player(pid: int):
    """ Get player from DUPR by ID """
    dupr_auth()
    get_player_from_dupr(pid)


@click.command()
@click.argument("pid")
def delete_player(pid: int):
    """ Get player from DUPR if necessary """
    logger.debug(f"delete player {pid} from database")
    pass


@click.command()
def update_ratings():
    dupr_auth()
    update_ratings_from_dupr()


@click.command()
def test_db():
    dupr_auth()
    with Session(eng) as sess:
        # Has to use "has" not "any" because it is 1=1? Also need to have something
        # in the has() function
        # use sess.scalars instead of execute(...).scalars() for more concise use
        dupr_ids = sess.scalars(select(Player.dupr_id).where(
            ~Player.rating.has(Rating.doubles)))
    for i in dupr_ids:
        print(i)


@click.command()
def get_all_players():
    dupr_auth()
    get_all_players_from_dupr()


@click.command()
@click.argument("dupr_id")
def get_matches(dupr_id: int):
    """ Get match history for specified player """
    dupr_auth()
    get_matches_from_dupr(dupr_id)


@click.command()
def get_data():
    """ Update all data """
    logger.info("Getting data from DUPR...")
    dupr_auth()
    get_all_players_from_dupr()
    with Session(eng) as sess:
        for p in sess.execute(select(Player)).scalars():
            print(type(p))
            get_matches_from_dupr(p.dupr_id)

    update_ratings_from_dupr()


@click.group()
def cli():
    pass


if __name__ == "__main__":
    logger.add("duprly_{time}.log")
    cli.add_command(get_data)
    cli.add_command(write_excel)
    cli.add_command(stats)
    cli.add_command(get_all_players)
    cli.add_command(get_player)
    cli.add_command(delete_player)
    cli.add_command(get_matches)
    cli.add_command(update_ratings)
    cli.add_command(test_db)
    cli()
