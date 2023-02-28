import os
import requests
from loguru import logger
import json

"""
    see
    https://api.dupr.gg/swagger-ui/index.html#/Club/getAllMembersUsingPOST

"""


class DuprClient(object):

    def __init__(self):
        self.env_path = os.path.expanduser('~/.duprly_config')
        logger.debug(self.env_path)
        self.env_url = 'https://api.dupr.gg'
        self.version = "v1.0"

        self.access_token = None
        self.refresh_token = None  # from login
        self.failed = False  # Strange way to return error, for now TBD

        self.load_token()

    def load_token(self):
        """ Load access token stored locally if available """
        try:
            with open(self.env_path, "r") as f:
                data = json.load(f)
                logger.debug(f"{data['access_token'][:10]}...")
                self.access_token = data['access_token']
        except FileNotFoundError:
            pass

    def save_token(self):
        """ Save  access token to disk, in plain json text
        """
        try:
            with open(self.env_path, "w") as f:
                data = {
                    'access_token': self.access_token
                }
                json.dump(data, f)
        except FileNotFoundError:
            # TODO: This is the wrong exception to catch!
            pass

    def u(self, parts):
        url = f'{self.env_url}{parts}'
        logger.debug(url)
        return url

    def ppj(self, data):
        """ Pretty Print Json for debug """
        logger.debug(json.dumps(data, indent=4))

    def save_json_to_file(self, name: str, data: dict):
        """ Save raw json to file for later use """
        with open(f"{name}.json", 'w') as f:
            json.dump(data, f)

    def load_json_from_file(self, name: str) -> dict:
        """
            Load previously saved json from file.
            Now return Marshmallow'ed json...

            Note that because our API returns a list of objects sometimes,
            and just one large objects other time, we need to
            convert it differently via Marshmallow
        """
        with open(f"{name}.json", 'r') as f:
            jdata = json.load(f)
            try:
                many = type(jdata) == list
                data = self.schemas[name].load(jdata, many=many)
            except ValidationError as error:
                logger.error(error.messages)
                logger.error(error.field_name)
            return data

    def auth_user(self, username: str, password: str):
        """ This is the external callable auth method.
            It handles a saved refresh_token, no need to re-login, or
            login and refresh
        """
        if self.access_token:
            return
            # test for specific error code?
        else:
            rc = self.login_user(username, password)
            return rc

    def login_user(self, username: str, password: str):
        """ Low level just do login (will need refresh after) """
        body = {
            'email': username,
            "password": password,
        }
        logger.debug(f'login user: {username}')
        r = requests.post(self.u('/auth/v1.0/login/'), json=body)
        logger.debug(f'login user: {r.status_code}')
        logger.debug(f'login user: {r.request.url}')
        if r.status_code == 200:
            data = r.json()
            self.ppj(data)
            self.access_token = data.get('result').get('accessToken')
            logger.debug(f'access token: {self.access_token[:10]}...')
            self.save_token()
        return r.status_code

    def headers(self):
        return {
            'Authorization': f'Bearer {self.access_token}'
        }

    def refresh_user(self):
        body = {
            'token': self.refresh_token
        }
        logger.debug("refresh user:")
        r = requests.post(self.u('/user/token/refresh/'), json=body)
        logger.debug(f'refresh user: {r.status_code}')
        if r.status_code == 200:
            self.access_token = r.json().get('token')
            logger.debug(f'access token: {self.access_token[:10]}...')
        return r.status_code

    def dupr_get(self, url, name: str = ""):
        logger.debug(f'GET: {name} : {url}')
        r = requests.get(self.u(url), headers=self.headers())  # , params=data)
        logger.debug(f'return: {r.status_code}')
        if r.status_code == 403:
            rc = self.refresh_user()
            if rc == 200:
                logger.debug(f'GET: {url}')
                r = requests.get(self.u(url), headers=self.headers())  # , params=data)
                logger.debug(f'return: {r.status_code}')
        self.failed = r.status_code != 200
        return r

    def dupr_post(self, url, json_data=None, name: str = ""):
        logger.debug(f'POST: {name} : {url}')
        headers = self.headers()
#         headers["Content-Type"] = "application/json"
#         headers["origin"] = "https://mydupr.com"
#        headers["referer"] = "https://mydupr.com/"

        r = requests.post(self.u(url), headers=headers,  json=json_data)
        logger.debug(f'return: {r.status_code}')
        if r.status_code == 4031:
            rc = self.refresh_user()
            if rc == 200:
                logger.debug(f'POST: {url}')
                r = requests.post(self.u(url), headers=self.headers())  # , params=data)
                logger.debug(f'return: {r.status_code}')
        self.failed = r.status_code != 200
        return r

    def get_profile(self):
        r = self.dupr_get(f'/user/{self.version}/profile/', "get_profile")
        if r.status_code == 200:
            self.ppj(r.json())
        return r.status_code

    def get_player(self, player_id: str):
        r = self.dupr_get(f'/player/{self.version}/{player_id}', "get_player")
        if r.status_code == 200:
            self.ppj(r.json())
            return r.status_code, r.json()["result"]
        else:
            return r.status_code, None

    def get_club(self, club_id: str):
        r = self.dupr_get(f'/club/{self.version}/{club_id}', "get_club")
        if r.status_code == 200:
            self.ppj(r.json())
        return r.status_code

    def get_member_match_history_p(self, member_id: str):
        page_data = {
            "filters": {},
            "sort": {
                "order": "DESC",
                "parameter": "MATCH_DATE",
                },
            "limit": 10,
            "offset": 0
        }
        offset = 0
        hit_data = []
        while offset is not None:
            r = self.dupr_post(f'/player/{self.version}/{member_id}/history',
                               page_data,
                               name="get_member_match_history")
            if r.status_code == 200:
                offset, hits = self.handle_paging(r.json())
                hit_data.extend(hits)
                page_data["offset"] = offset
        self.ppj(page_data)
        return r.status_code, hit_data

    def get_member_match_history(self, member_id: str):
        offset = 0
        hit_data = []
        while offset is not None:
            r = self.dupr_get(f'/player/{self.version}/{member_id}/history?limit=100&offset={offset}',
                              name="get_member_match_history")
            if r.status_code == 200:
                offset, hits = self.handle_paging(r.json())
                hit_data.extend(hits)
        self.ppj(hit_data)
        return r.status_code, hit_data

    def handle_paging(self, json_data):
        """
        Handle results that are paged.
        use like this:
        
            while offset is not None:
                dupr_get
                offset, hits = handle_paging(response.json())

        """
        result = json_data["result"]
        total = result["total"]
        offset = result["offset"]
        limit = result["limit"]
        hits = result["hits"]
        if offset + limit < total:
            # there is more
            return offset + limit, hits
        else:
            return None, hits

    def get_members_by_club(self, club_id: str):
        """
        this call is a post call because it supports query and filter.
        """
        data = {
            "exclude": [],
            "limit": 20,
            "filter": {
                "lat": 42.4609077,
                "lng": -71.2220832
                },
            "offset": 0,
            "query": "*"
            }
        offset = 0
        pdata = []
        while (offset is not None):
            data["offset"] = offset
            r = self.dupr_post(f'/club/{club_id}/members/v1.0/all', json_data=data, name="get_member_by_club")
            if r.status_code == 200:
                # self.ppj(r.json())
                offset, hits = self.handle_paging(r.json())
                logger.debug(f'offset: {offset}')
                pdata.extend(hits)

        self.ppj(pdata)
        return r.status_code, pdata
