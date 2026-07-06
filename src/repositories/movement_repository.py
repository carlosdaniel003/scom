from src.database.connection import database_connection


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
            resulting = previous + quantity if normalized_type == "ENTRADA" else previous - quantity
            if resulting < 0:
                raise ValueError("A saída não pode ser maior que a quantidade disponível.")

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

    @staticmethod
    def list_recent(limit: int = 100) -> list[dict]:
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
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
