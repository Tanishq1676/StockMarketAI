"""Drop the predictions table so create_all recreates it with the fixed schema."""

import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "backend"))
from app.database import engine
from sqlalchemy import text


def main():
    with engine.connect() as c:
        tables = [r[0] for r in c.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
        print("tables before:", tables)
        if "predictions" in tables:
            c.execute(text("DROP TABLE predictions"))
            print("dropped predictions")
        cols = c.execute(text("PRAGMA table_info(predictions)")).fetchall() if "predictions" in tables else []
        dc = [col for col in cols if col[1] == "direction_correct"]
        print("predictions.direction_correct:", [(col[1], col[2], col[3]) for col in dc])
    # now recreate
    from app.database import Base
    from app import models  # noqa

    Base.metadata.create_all(bind=engine)
    with engine.connect() as c:
        cols = c.execute(text("PRAGMA table_info(predictions)")).fetchall()
        print("predictions.direction_correct after recreate:", [(col[1], col[2], col[3]) for col in cols if col[1] == "direction_correct"])


if __name__ == "__main__":
    main()
