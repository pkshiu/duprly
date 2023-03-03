set dotenv-load := true
DB_PATH := "dupr.sqlite"


data:
	python duprly.py get-data

report:
	python duprly.py write-excel;open dupr.xlsx

web: rating_view player_view
	datasette {{DB_PATH}}


rating_view:
	sqlite-utils drop-view {{DB_PATH}} rating_view --ignore
	sqlite-utils create-view {{DB_PATH}} rating_view 'Select player.id, dupr_id, full_name, gender, age, image_url, email, doubles, singles, doubles_verified from player, rating where rating.player_id = player.id order by first_name desc'

player_view:
	sqlite-utils drop-view {{DB_PATH}} player_view --ignore
	sqlite-utils create-view {{DB_PATH}} player_view 'select player.id, dupr_id, full_name, gender, age, email, doubles, singles, doubles_verified, count(match.id) from player, rating, match, match_team, match_team_player where rating.player_id = player.id and match_team_player.player_id = player.id and match_team_player.match_team_id = match_team.id and match_team.match_id = match.id group by player.id order by match.id desc'

move_db:
	- mv dupr.sqlite dupr_`date +%Y%m%d_%H%M`.sqlite

qtest_1:
	python duprly.py get-player 6493661183
	python duprly.py get-player 6335922641
	python duprly.py get-player 6923845911
	python duprly.py get-matches 6493661183
	python duprly.py update-ratings
	python duprly.py update-ratings

qtest: move_db qtest_1 web


