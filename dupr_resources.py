"""
"""
from datetime import date
from operator import attrgetter
from loguru import logger


class Player:
    def __init__(self):
        self.id = None
        self.dupr_id = ""
        self.full_name = ""
        self.image_url = ""        
        self.email = ""
        self.gender = ""
        self.age = 0

        self.singles = "NR"
        self.singles_verified = "NR"
        self.singles_provisional = False

        self.doubles = "NR"
        self.doubles_verified = "NR"
        self.doubles_provisional = False

    def from_json(self, d: dict) -> 'Player':
        try:
            self.id = d.get("id")
            self.dupr_id = d.get("duprId")
            self.full_name = d.get("fullName")
            self.image_url = d.get("imageUrl")

            self.email = d.get("email")
            self.gender = d.get("gender")
            self.age = d.get("age")

            self.singles = d.get("singles")
            self.singlesVerified = d.get("singlesVerified")
            self.singlesProvisional = d.get("singlesProvisional")

            self.doubles = d.get("doubles")
            self.doublesVerified = d.get("doublesVerified")
            self.doublesProvisional = d.get("doublesProvisional")
            return self
        except:
            logger.exception(d)
            raise


class Team:
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


class Match:
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