import csv
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from src.database.connection import database_connection
from src.utils.paths import DATA_DIR, DATABASE_PATH, ensure_directories


class BackupError(RuntimeError):
    pass


class BackupService:
    MAX_LOG_FILES = 10
    MAX_RECORDS_PER_FILE = 10_000
    LOG_DIRECTORY = DATA_DIR / "movement_logs"
    LOG_PREFIX = "movimentacoes_"
    LOG_HEADERS = (
        "ID",
        "Data e hora",
        "Código interno",
        "Peça",
        "Categoria",
        "Modelo",
        "Tipo",
        "Quantidade",
        "Saldo anterior",
        "Saldo resultante",
        "Responsável",
        "Motivo",
    )

    @staticmethod
    def backup_database(destination: str | Path) -> Path:
        ensure_directories()
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if destination_path.resolve() == DATABASE_PATH.resolve():
                raise BackupError(
                    "Escolha um local diferente do banco de dados em uso."
                )

            source = sqlite3.connect(DATABASE_PATH)
            target = sqlite3.connect(destination_path)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
        except BackupError:
            raise
        except (OSError, sqlite3.Error) as error:
            raise BackupError(f"Não foi possível criar o backup: {error}") from error

        return destination_path

    @classmethod
    def sync_movement_logs(cls) -> int:
        cls._ensure_log_directory()
        last_logged_id = cls._last_logged_id()

        try:
            with database_connection() as connection:
                rows = connection.execute(
                    """
                    SELECT
                        sm.id,
                        sm.created_at,
                        p.internal_code,
                        p.name AS part_name,
                        c.name AS category_name,
                        COALESCE(m.name, '') AS model_name,
                        sm.movement_type,
                        sm.quantity,
                        sm.previous_quantity,
                        sm.resulting_quantity,
                        sm.responsible,
                        sm.reason
                    FROM stock_movements sm
                    JOIN parts p ON p.id = sm.part_id
                    JOIN categories c ON c.id = p.category_id
                    LEFT JOIN models m ON m.id = p.model_id
                    WHERE sm.id > ?
                    ORDER BY sm.id ASC
                    """,
                    (last_logged_id,),
                ).fetchall()
        except sqlite3.Error as error:
            raise BackupError(
                f"Não foi possível consultar as movimentações: {error}"
            ) from error

        try:
            for row in rows:
                cls._append_log_row(dict(row))
        except (OSError, csv.Error, ValueError) as error:
            raise BackupError(
                f"Não foi possível atualizar os arquivos de log: {error}"
            ) from error

        return len(rows)

    @classmethod
    def export_movement_logs(cls, destination: str | Path) -> Path:
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        cls.sync_movement_logs()
        cls._ensure_empty_log_file()

        try:
            with zipfile.ZipFile(
                destination_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                for log_file in cls._log_files():
                    archive.write(log_file, arcname=log_file.name)
        except (OSError, zipfile.BadZipFile) as error:
            raise BackupError(
                f"Não foi possível exportar os logs: {error}"
            ) from error

        return destination_path

    @classmethod
    def _ensure_log_directory(cls) -> None:
        ensure_directories()
        cls.LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _log_files(cls) -> list[Path]:
        cls._ensure_log_directory()
        return sorted(
            cls.LOG_DIRECTORY.glob(f"{cls.LOG_PREFIX}*.csv"),
            key=cls._file_sequence,
        )

    @classmethod
    def _file_sequence(cls, path: Path) -> int:
        try:
            return int(path.stem.removeprefix(cls.LOG_PREFIX))
        except ValueError:
            return 0

    @classmethod
    def _create_log_file(cls, sequence: int) -> Path:
        path = cls.LOG_DIRECTORY / f"{cls.LOG_PREFIX}{sequence:06d}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(cls.LOG_HEADERS)
        return path

    @classmethod
    def _ensure_empty_log_file(cls) -> None:
        if not cls._log_files():
            cls._create_log_file(1)

    @classmethod
    def _active_log_file(cls) -> Path:
        files = cls._log_files()
        if not files:
            return cls._create_log_file(1)

        active_file = files[-1]
        if cls._record_count(active_file) < cls.MAX_RECORDS_PER_FILE:
            return active_file

        next_sequence = cls._file_sequence(active_file) + 1
        active_file = cls._create_log_file(next_sequence)
        cls._rotate_log_files()
        return active_file

    @classmethod
    def _record_count(cls, path: Path) -> int:
        with path.open("r", newline="", encoding="utf-8-sig") as file:
            return max(sum(1 for _ in file) - 1, 0)

    @classmethod
    def _rotate_log_files(cls) -> None:
        files = cls._log_files()
        excess = len(files) - cls.MAX_LOG_FILES
        for old_file in files[:max(excess, 0)]:
            old_file.unlink(missing_ok=True)

    @classmethod
    def _last_logged_id(cls) -> int:
        files = cls._log_files()
        if not files:
            return 0

        latest_file = files[-1]
        last_id = 0
        with latest_file.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.reader(file, delimiter=";")
            next(reader, None)
            for row in reader:
                if row and row[0].isdigit():
                    last_id = int(row[0])
        return last_id

    @classmethod
    def _append_log_row(cls, movement: dict) -> None:
        active_file = cls._active_log_file()
        values = (
            movement["id"],
            movement["created_at"],
            movement["internal_code"],
            movement["part_name"],
            movement["category_name"],
            movement["model_name"] or "—",
            movement["movement_type"],
            movement["quantity"],
            movement["previous_quantity"],
            movement["resulting_quantity"],
            movement["responsible"],
            movement["reason"],
        )
        with active_file.open("a", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(values)

    @staticmethod
    def default_database_filename() -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"SCOM_backup_{timestamp}.db"

    @staticmethod
    def default_logs_filename() -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"SCOM_logs_movimentacoes_{timestamp}.zip"
