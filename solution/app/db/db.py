import os

from dotenv import load_dotenv
from psycopg2.pool import ThreadedConnectionPool

load_dotenv()

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")

# Here we open the connection pool
db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
sql_pool = ThreadedConnectionPool(1, 20, dsn=db_url)


def sql_init_cursor():
    conn = sql_pool.getconn()
    cursor = conn.cursor()
    return cursor


def sql_commit_close():
    conn = sql_pool.getconn()
    cursor = conn.cursor()
    return cursor
