import sys, os

# Must be set BEFORE any application module is imported so that database.py
# binds its engine to SQLite rather than attempting to connect to Postgres.
os.environ["DATABASE_URL"] = "sqlite:///./test_api.db"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
