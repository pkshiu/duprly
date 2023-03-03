set dotenv-load := true
DB_PATH := "dupr.sqlite"


data:
	python duprly.py get-data

report:
	python duprly.py write-excel;open dupr.xlsx

web:
	datasette {{DB_PATH}}


rating_view:
	sqlite-utils drop-view {{DB_PATH}} rating_view --ignore
	sqlite-utils create-view {{DB_PATH}} rating_view 'select player.id, dupr_id, full_name, gender, age, image_url, email, doubles, singles, doubles_verified from player, rating where rating.player_id = player.id order by first_name desc'

qtest_0:
	- rm dupr.sqlite

qtest_1:
	python duprly.py get-player 6493661183
	python duprly.py get-player 6335922641
	python duprly.py get-player 6923845911
	python duprly.py get-matches 6493661183
	python duprly.py update-ratings
	python duprly.py update-ratings

qtest: qtest_0 rating_view qtest_1 web

reset: qtest_0 rating_view

