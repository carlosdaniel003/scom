from typing import Any

from src.database.connection import database_connection
from src.models.part import PartInput


class PartRepository:
    @staticmethod
    def _get_or_create_model(connection, model_name: str, category_id: int) -> int | None:
        model_name = model_name.strip()
        if not model_name:
            return None

        row = connection.execute(
            "SELECT id FROM models WHERE name = ? COLLATE NOCASE",
            (model_name,),
        ).fetchone()
        if row:
            return int(row["id"])

        cursor = connection.execute(
            "INSERT INTO models (name, category_id) VALUES (?, ?)",
            (model_name, category_id),
        )
        return int(cursor.lastrowid)

    @classmethod
    def create(cls, part: PartInput) -> int:
        with database_connection() as connection:
            model_id = cls._get_or_create_model(
                connection, part.model_name, part.category_id
            )
            cursor = connection.execute(
                """
                INSERT INTO parts (
                    image_path, internal_code, name, description, category_id,
                    component_value, component_unit, model_id, current_quantity,
                    minimum_quantity, physical_location, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    part.image_path,
                    part.internal_code.strip(),
                    part.name.strip(),
                    part.description.strip(),
                    part.category_id,
                    part.component_value.strip(),
                    part.component_unit.strip(),
                    model_id,
                    part.current_quantity,
                    part.minimum_quantity,
                    part.physical_location.strip(),
                    part.notes.strip(),
                ),
            )
            part_id = int(cursor.lastrowid)

            if part.current_quantity > 0:
                connection.execute(
                    """
                    INSERT INTO stock_movements (
                        part_id, movement_type, quantity, previous_quantity,
                        resulting_quantity, reason, responsible
                    ) VALUES (?, 'ENTRADA', ?, 0, ?, ?, ?)
                    """,
                    (
                        part_id,
                        part.current_quantity,
                        part.current_quantity,
                        "Saldo inicial do cadastro",
                        "Cadastro inicial",
                    ),
                )
            return part_id

    @staticmethod
    def update(part_id: int, part: PartInput) -> None:
        with database_connection() as connection:
            model_id = PartRepository._get_or_create_model(
                connection, part.model_name, part.category_id
            )
            connection.execute(
                """
                UPDATE parts SET
                    image_path = ?, internal_code = ?, name = ?, description = ?,
                    category_id = ?, component_value = ?, component_unit = ?,
                    model_id = ?, minimum_quantity = ?, physical_location = ?,
                    notes = ?, updated_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (
                    part.image_path,
                    part.internal_code.strip(),
                    part.name.strip(),
                    part.description.strip(),
                    part.category_id,
                    part.component_value.strip(),
                    part.component_unit.strip(),
                    model_id,
                    part.minimum_quantity,
                    part.physical_location.strip(),
                    part.notes.strip(),
                    part_id,
                ),
            )

    @staticmethod
    def list_models(category_id: int | None = None) -> list[str]:
        query = "SELECT name FROM models"
        params: tuple[Any, ...] = ()
        if category_id is not None:
            query += " WHERE category_id = ? OR category_id IS NULL"
            params = (category_id,)
        query += " ORDER BY name COLLATE NOCASE"

        with database_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [str(row["name"]) for row in rows]

    @staticmethod
    def list_locations() -> list[str]:
        with database_connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT TRIM(physical_location) AS physical_location
                FROM parts
                WHERE TRIM(COALESCE(physical_location, '')) <> ''
                ORDER BY physical_location COLLATE NOCASE
                """
            ).fetchall()
        return [str(row["physical_location"]) for row in rows]

    @staticmethod
    def search(search_text: str = "", status_filter: str = "all") -> list[dict]:
        terms = f"%{search_text.strip()}%"
        conditions = [
            """
            (
                p.internal_code LIKE ? OR p.name LIKE ? OR
                COALESCE(p.description, '') LIKE ? OR c.name LIKE ? OR
                COALESCE(m.name, '') LIKE ? OR p.physical_location LIKE ?
            )
            """
        ]
        params: list[Any] = [terms] * 6

        if status_filter == "low":
            conditions.append("p.current_quantity > 0 AND p.current_quantity <= p.minimum_quantity")
        elif status_filter == "empty":
            conditions.append("p.current_quantity = 0")
        elif status_filter == "available":
            conditions.append("p.current_quantity > p.minimum_quantity")

        query = f"""
            SELECT
                p.id, p.image_path, p.internal_code, p.name, p.description,
                p.category_id, c.name AS category_name,
                p.component_value, p.component_unit,
                COALESCE(m.name, '') AS model_name,
                p.current_quantity, p.minimum_quantity,
                p.physical_location, p.notes,
                p.created_at, p.updated_at,
                CASE
                    WHEN p.current_quantity = 0 THEN 'Sem estoque'
                    WHEN p.current_quantity <= p.minimum_quantity THEN 'Estoque baixo'
                    ELSE 'Disponível'
                END AS stock_status
            FROM parts p
            JOIN categories c ON c.id = p.category_id
            LEFT JOIN models m ON m.id = p.model_id
            WHERE {' AND '.join(conditions)}
            ORDER BY p.name COLLATE NOCASE, p.internal_code COLLATE NOCASE
        """

        with database_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(part_id: int) -> dict | None:
        with database_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    p.*, c.name AS category_name,
                    c.requires_component_value, c.value_label, c.default_unit,
                    COALESCE(m.name, '') AS model_name
                FROM parts p
                JOIN categories c ON c.id = p.category_id
                LEFT JOIN models m ON m.id = p.model_id
                WHERE p.id = ?
                """,
                (part_id,),
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def dashboard_totals() -> dict:
        with database_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_parts,
                    COALESCE(SUM(current_quantity), 0) AS total_quantity,
                    COALESCE(SUM(CASE WHEN current_quantity = 0 THEN 1 ELSE 0 END), 0) AS empty_count,
                    COALESCE(SUM(CASE
                        WHEN current_quantity > 0 AND current_quantity <= minimum_quantity
                        THEN 1 ELSE 0 END), 0) AS low_count
                FROM parts
                """
            ).fetchone()
        return dict(row)
