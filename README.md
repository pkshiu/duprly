

## API Issues

- Player call returns no DuprId field.
- double (and singles?) rating is always returned in the ratings field, not the verified field even
  if the rating is verified according to the isDoublesVerified field
- Match history calls returns teams with players but only minimal fields, and the players have a different type of DuprId

## Design Issues

### Saving Match Data

- because different player data gets returned, saving a composite object is messy

