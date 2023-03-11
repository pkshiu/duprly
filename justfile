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

v4 := '''
select
  m.name,
  m.date,
  team_1_score,
  p1.full_name,
  r1.doubles,
  p2.full_name,
  r2.doubles,
  team_2_score,
  p3.full_name,
  r3.doubles,
  p4.full_name,
  r4.doubles
from
  match_detail as mt,
  match as m
  left join player as p1 on p1.id = team_1_player_1_id
  left join player as p2 on p2.id = team_1_player_2_id
  left join player as p3 on p3.id = team_2_player_1_id
  left join player as p4 on p4.id = team_2_player_2_id
  left join rating as r1 on r1.id = team_1_player_1_id
  left join rating as r2 on r2.id = team_1_player_2_id
  left join rating as r3 on r3.id = team_2_player_1_id
  left join rating as r4 on r4.id = team_2_player_2_id
where
  mt.match_id = m.id
order by
  m.date
'''
match_report_view:
	sqlite-utils create-view --replace {{DB_PATH}} match_report_view "{{v4}}"


move_db:
	- mv dupr.sqlite dupr_`date +%Y%m%d_%H%M`.sqlite



