
import os
from sqlalchemy import create_engine, text


def main():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    # Use the installed psycopg2 PostgreSQL driver.
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+psycopg2://",
            1,
        )
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql+psycopg2://",
            1,
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 15},
    )

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT NOW()"))
            print(
                "Supabase database check succeeded:",
                result.scalar(),
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
