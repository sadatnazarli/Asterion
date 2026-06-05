import sys
sys.path.insert(0, '.')
from app.db.session import transaction
with transaction() as conn:
    sql = open('app/db/migrations/0010_portfolio_partial_data.sql').read()
    conn.execute(sql)
    print("Migration applied!")
