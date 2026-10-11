
import os
from sqlalchemy import create_engine, text

def main():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 15},
    )

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT NOW()")
            )
            print(f"Supabase database check succeeded: {result.scalar()}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
