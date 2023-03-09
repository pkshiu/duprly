set dotenv-load := true
DB_PATH := "dupr.sqlite"

stats:
	python duprly.py stats
	
data:
	python duprly.py get-data

report:
	python duprly.py write-excel;open dupr.xlsx

web: rating_view player_view match_player_view match_detail_view
	datasette {{DB_PATH}}


rating_view:
	sqlite-utils drop-view {{DB_PATH}} rating_view --ignore
	sqlite-utils create-view {{DB_PATH}} rating_view 'Select player.id, dupr_id, full_name, gender, age, image_url, email, doubles, singles, doubles_verified from player, rating where rating.player_id = player.id order by first_name desc'

player_view:
	sqlite-utils drop-view {{DB_PATH}} player_view --ignore
	sqlite-utils create-view {{DB_PATH}} player_view 'select player.id, dupr_id, full_name, gender, age, email, doubles, singles, doubles_verified, count(match.id) from player, rating, match, match_team, match_team_player where rating.player_id = player.id and match_team_player.player_id = player.id and match_team_player.match_team_id = match_team.id and match_team.match_id = match.id group by player.id order by match.id desc'

v2 := '''
select
  m.id as match_id,
  p.full_name
from
  match as m,
  match_team as mt,
  match_team_player as mtp,
  player as p
where
  m.id = mt.match_id
  and mtp.match_team_id = mt.id
  and mtp.player_id = p.id
'''

match_player_view:
	sqlite-utils create-view --replace {{DB_PATH}} match_player_view "{{v2}}"

v3 := '''
select
  m.id as match_id,
  m.name,
  m.date,
  p.full_name,
  r.doubles,
  mt.id as team_id,
  mpv.full_name as player
  
from
  match as m,
  match_team as mt,
  match_team_player as mtp,
  player as p,
  rating as r,
  match_player_view as mpv
where
  m.id = mt.match_id
  and mtp.match_team_id = mt.id
  and mtp.player_id = p.id
  and r.player_id = p.id
  and m.id = mpv.match_id
order by m.date
'''

match_detail_view:
	sqlite-utils create-view --replace {{DB_PATH}} match_detail_view "{{v3}}"

move_db:
	- mv dupr.sqlite dupr_`date +%Y%m%d_%H%M`.sqlite



