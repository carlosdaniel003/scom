from typing import Any

from src.database.connection import database_connection
from src.models.part import PartInput
from src.services.backup_service import BackupError
from src.services.movement_log_service import MovementLogService


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

    @staticmethod
    def _internal_code_exists(
        connection,
        internal_code: str,
        exclude_part_id: int | None = None,
    ) -> bool:
        normalized_code = internal_code.strip()
        if not normalized_code:
            return False

        query = "SELECT 1 FROM parts WHERE internal_code = ? COLLATE NOCASE"
        params: list[Any] = [normalized_code]
        if exclude_part_id is not None:
            query += " AND id <> ?"
            params.append(exclude_part_id)
        query += " LIMIT 1"

        return connection.execute(query, tuple(params)).fetchone() is not None

    @classmethod
    def create(cls, part: PartInput) -> int:
        has_initial_movement = part.current_quantity > 0

        with database_connection() as connection:
            if cls._internal_code_exists(connection, part.internal_code):
                raise ValueError(
                    "Já existe uma peça cadastrada com esse código interno."
                )

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

            if has_initial_movement:
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

        if has_initial_movement:
            try:
                MovementLogService.sync()
            except BackupError:
                pass

        return part_id

    @staticmethod
    def update(part_id: int, part: PartInput) -> None:
        with database_connection() as connection:
            if PartRepository._internal_code_exists(
                connection,
                part.internal_code,
                exclude_part_id=part_id,
            ):
                raise ValueError(
                    "Já existe uma peça cadastrada com esse código interno."
                )

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
    def _search_conditions(
        search_text: str,
        status_filter: str,
    ) -> tuple[list[str], list[Any]]:
        search_terms = [term for term in search_text.strip().split() if term]
        conditions: list[str] = []
        params: list[Any] = []

        for term in search_terms:
            pattern = f"%{term}%"
            conditions.append(
                """
                (
                    p.internal_code LIKE ? OR
                    p.name LIKE ? OR
                    COALESCE(p.description, '') LIKE ? OR
                    c.name LIKE ? OR
                    COALESCE(m.name, '') LIKE ? OR
                    p.physical_location LIKE ? OR
                    COALESCE(p.component_value, '') LIKE ? OR
                    COALESCE(p.component_unit, '') LIKE ? OR
                    (COALESCE(p.component_value, '') || ' ' ||
                     COALESCE(p.component_unit, '')) LIKE ?
                )
                """
            )
            params.extend([pattern] * 9)

        if not conditions:
            conditions.append("1 = 1")

        if status_filter == "low":
            conditions.append(
                "p.current_quantity > 0 AND "
                "p.current_quantity <= p.minimum_quantity"
            )
        elif status_filter == "empty":
            conditions.append("p.current_quantity = 0")
        elif status_filter == "available":
            conditions.append("p.current_quantity > p.minimum_quantity")

        return conditions, params

    @classmethod
    def search_paginated(
        cls,
        search_text: str = "",
        status_filter: str = "all",
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        safe_page_size = min(max(int(page_size), 1), 200)
        conditions, params = cls._search_conditions(search_text, status_filter)
        where_clause = " AND ".join(conditions)

        count_query = f"""
            SELECT COUNT(*) AS total
            FROM parts p
            JOIN categories c ON c.id = p.category_id
            LEFT JOIN models m ON m.id = p.model_id
            WHERE {where_clause}
        """

        with database_connection() as connection:
            total = int(connection.execute(count_query, params).fetchone()["total"])
            total_pages = max(1, (total + safe_page_size - 1) // safe_page_size)
            current_page = min(max(int(page), 1), total_pages)
            offset = (current_page - 1) * safe_page_size

            rows = connection.execute(
                f"""
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
                        WHEN p.current_quantity <= p.minimum_quantity
                            THEN 'Estoque baixo'
                        ELSE 'Disponível'
                    END AS stock_status
                FROM parts p
                JOIN categories c ON c.id = p.category_id
                LEFT JOIN models m ON m.id = p.model_id
                WHERE {where_clause}
                ORDER BY p.name COLLATE NOCASE,
                         p.internal_code COLLATE NOCASE
                LIMIT ? OFFSET ?
                """,
                [*params, safe_page_size, offset],
            ).fetchall()

        return {
            "items": [dict(row) for row in rows],
            "total": total,
            "page": current_page,
            "pages": total_pages,
            "page_size": safe_page_size,
        }

    @classmethod
    def search(cls, search_text: str = "", status_filter: str = "all") -> list[dict]:
        conditions, params = cls._search_conditions(search_text, status_filter)
        where_clause = " AND ".join(conditions)

        with database_connection() as connection:
            rows = connection.execute(
                f"""
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
                        WHEN p.current_quantity <= p.minimum_quantity
                            THEN 'Estoque baixo'
                        ELSE 'Disponível'
                    END AS stock_status
                FROM parts p
                JOIN categories c ON c.id = p.category_id
                LEFT JOIN models m ON m.id = p.model_id
                WHERE {where_clause}
                ORDER BY p.name COLLATE NOCASE,
                         p.internal_code COLLATE NOCASE
                """,
                params,
            ).fetchall()
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
