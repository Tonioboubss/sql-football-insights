import sqlite3

conn = sqlite3.connect("football.db")
cur = conn.cursor()

### teams (unique) total number 
# cur.execute("""
# SELECT COUNT(*) FROM teams;
# """)

### Competition total number
# cur.execute("""
# SELECT COUNT(*) FROM competitions;
# """)

### Competition_teams total number
# cur.execute("""
# SELECT COUNT(*) FROM team_competitions;
# """)

### Matches total number
cur.execute("""
SELECT COUNT(*) FROM matches;
""")

for row in cur.fetchall():
    print(row)

conn.close()