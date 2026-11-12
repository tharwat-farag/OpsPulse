from sqlalchemy import text

from warehouse.db_connection import get_database_engine


def main():
    engine = get_database_engine()

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), current_user")
        )

        database_name, username = result.fetchone()

        print(f"Database: {database_name}")
        print(f"User: {username}")
        print("Database connection successful!")


if __name__ == "__main__":
    main()