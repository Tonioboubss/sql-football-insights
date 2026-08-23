import sqlite3

conn = sqlite3.connect("football.db")
cur = conn.cursor()

""" Overview: how many matches per status? A fully completed season
should be almost entirely FINISHED, with maybe a rare AWARDED (forfeit)
or CANCELLED match."""

cur.execute("""
SELECT status, COUNT(*) FROM matches GROUP BY status;
""")
cur.execute("""
SELECT m.id, competition_id, th.name, ta.name, match_date, status, home_score, away_score
FROM matches m 
JOIN teams th ON th.id = m.home_team_id
JOIN teams ta ON ta.id = m.away_team_id
WHERE status = 'AWARDED';
""")

# cur.execute("""
# SELECT * FROM matches WHERE status = 'AWARDED';
# """)

""" The real check: any FINISHED match with a missing score would indicate
a parsing/loading bug, not a legitimate data state."""

# cur.execute("""
# SELECT id, external_id, competition_id, home_team_id, away_team_id, match_date, status
# FROM matches
# WHERE status = 'FINISHED' AND (home_score IS NULL OR away_score IS NULL);
# """)

for row in cur.fetchall():
    print(row)

conn.close()