import sqlite3

conn = sqlite3.connect("football.db")
cur = conn.cursor()

cur.execute("""
SELECT match_date, points, points_before_match
FROM team_points_before_match
WHERE team_id = (SELECT id FROM teams WHERE name = 'Arsenal FC')
ORDER BY match_date
LIMIT 5;
""")

for row in cur.fetchall():
    print(row)

conn.close()