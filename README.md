# Introduction

This DUPR data downloader pulls player and match history data for all players belonging
to a club. This program pulls data form all the players that our players have played against
even if they are not in the club, so the dataset can get pretty big.

The data is stored in a local sqlite3 database via SQLAlchemy (I am working on a Mac).
This is my yet another attempt to master SQLAlchemy ORM.

After normalizing the data, I am using datasette to analyze the data. It is a great tool.
Check it out!

Lots of more work to be done..

## API Issues

Keeping a list of things I found. Note that this is NOT a public and supported API.
I am just documenting it as I try different calls.

- Player call returns no DuprId field.
- double (and singles?) rating is always returned in the ratings field, not the verified field even
  if the rating is verified according to the isDoublesVerified field
- Match history calls returns teams with players but only minimal fields, and the players have a different type of DuprId

## Design Issues

- because different player data gets returned between the match calls and the
  player calls, saving a player, which is a composite object, is messy
- don't yell at me for storing the user id and password in a plain text env file!
  Actually this is really bad practice - do not do it.

## ToDo

- fix the write_excel code -- which is still using the old tinyDB database interface
- write tests!

## SQLAlchemy notes

## Selecting directly into list of objects

- use session.scalar(select(Class).where().all()) instead of session.execute(...).scalars()
- returning objects cannot be use outside of the session scope afterwards!!?

## Joins and selecting columns

result = session.execute(
...     select(User.name, Address.email_address)
...     .join(User.addresses)
...     .order_by(User.id, Address.id)
