from src.database.connection import database_connection


class CategoryRepository:
    @staticmethod
    def list_all() -> list[dict]:
        with database_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, name, requires_component_value, value_label, default_unit
                FROM categories
                ORDER BY name
                """
            ).fetchall()
        return [dict(row) for row in rows]
