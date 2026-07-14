from typing import Any

from src.database.connection import database_connection
from src.services.backup_service import BackupError, BackupService


class MovementRepository:
    @staticmethod
    def create(
        part_id: int,
        movement_type: str,
        quantity: int,
        reason: str,
        responsible: str,
    ) -> None:
        normalized_type = movement_type.strip().upper()
        if normalized_type not in {"ENTRADA", "SAÍDA"}:
            raise ValueError("Tipo de movimentação inválido.")
        if quantity <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")

        with database_connection() as connection:
            row = connection.execute(
                "SELECT current_quantity FROM parts WHERE id = ?",
                (part_id,),
            ).fetchone()
            if not row:
                raise ValueError("Peça não encontrada.")

            previous = int(row["current_quantity"])
            resulting = (
                previous + quantity
                if normalized_type == "ENTRADA"
                else previous - quantity
            )
            if resulting < 0:
                raise ValueError(
                    "A saída não pode ser maior que a quantidade disponível."
                )

            connection.execute(
                """
                INSERT INTO stock_movements (
                    part_id, movement_type, quantity, previous_quantity,
                    resulting_quantity, reason, responsible
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    part_id,
                    normalized_type,
                    quantity,
                    previous,
                    resulting,
                    reason.strip(),
                    responsible.strip(),
                ),
            )
            connection.execute(
                """
                UPDATE parts
                SET current_quantity = ?, updated_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (resulting, part_id),
            )

        try:
            BackupService.sync_movement_logs()
        except BackupError:
            pass

    @staticmethod
    def list_recent(limit: int = 100) -> list[dict]:
        safe_limit = min(max(int(limit), 1), 1000)
        with database_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    sm.id, sm.movement_type, sm.quantity,
                    sm.previous_quantity, sm.resulting_quantity,
                    sm.reason, sm.responsible, sm.created_at,
                    p.internal_code, p.name AS part_name
                FROM stock_movements sm
                JOIN parts p ON p.id = sm.part_id
                ORDER BY sm.id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def summary() -> dict:
        with database_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(CASE
                        WHEN movement_type = 'ENTRADA' THEN 1 ELSE 0 END), 0)
                        AS entries,
                    COALESCE(SUM(CASE
                        WHEN movement_type = 'SAÍDA' THEN 1 ELSE 0 END), 0)
                        AS exits
                FROM stock_movements
                """
            ).fetchone()
        return dict(row)

    @staticmethod
    def _search_conditions(
        search_text: str,
        movement_filter: str,
    ) -> tuple[list[str], list[Any]]:
        conditions: list[str] = []
        params: list[Any] = []

        search_terms = [term for term in search_text.strip().split() if term]
        for term in search_terms:
            pattern = f"%{term}%"
            conditions.append(
                """
                (
                    sm.created_at LIKE ? OR
                    p.internal_code LIKE ? OR
                    p.name LIKE ? OR
                    sm.movement_type LIKE ? OR
                    sm.responsible LIKE ? OR
                    sm.reason LIKE ?
                )
                """
            )
            params.extend([pattern] * 6)

        if movement_filter in {"ENTRADA", "SAÍDA"}:
            conditions.append("sm.movement_type = ?")
            params.append(movement_filter)

        if not conditions:
            conditions.append("1 = 1")

        return conditions, params

    @classmethod
    def search_paginated(
        cls,
        search_text: str = "",
        movement_filter: str = "all",
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        safe_page_size = min(max(int(page_size), 1), 200)
        conditions, params = cls._search_conditions(
            search_text,
            movement_filter,
        )
        where_clause = " AND ".join(conditions)

        with database_connection() as connection:
            total = int(
                connection.execute(
                    f"""
                    SELECT COUNT(*) AS total
                    FROM stock_movements sm
                    JOIN parts p ON p.id = sm.part_id
                    WHERE {where_clause}
                    """,
                    params,
                ).fetchone()["total"]
            )

            total_pages = max(1, (total + safe_page_size - 1) // safe_page_size)
            current_page = min(max(int(page), 1), total_pages)
            offset = (current_page - 1) * safe_page_size

            rows = connection.execute(
                f"""
                SELECT
                    sm.id, sm.movement_type, sm.quantity,
                    sm.previous_quantity, sm.resulting_quantity,
                    sm.reason, sm.responsible, sm.created_at,
                    p.internal_code, p.name AS part_name
                FROM stock_movements sm
                JOIN parts p ON p.id = sm.part_id
                WHERE {where_clause}
                ORDER BY sm.id DESC
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
