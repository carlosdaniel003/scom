import csv
import json
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path

from src.database.connection import database_connection
from src.services.backup_service import BackupError
from src.utils.paths import DATA_DIR, ensure_directories


class MovementLogService:
    MAX_LOG_FILES = 10
    MAX_RECORDS_PER_FILE = 10_000
    LOG_DIRECTORY = DATA_DIR / "movement_logs"
    LOG_PREFIX = "movimentacoes_"
    STATE_PATH = LOG_DIRECTORY / ".movement_log_state.json"
    HEADERS = (
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

    @classmethod
    def sync(cls) -> int:
        try:
            cls._ensure_directory()
            state = cls._load_state()

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
                    (state["last_id"],),
                ).fetchall()

            for row in rows:
                if state["records"] >= cls.MAX_RECORDS_PER_FILE:
                    state["sequence"] += 1
                    state["records"] = 0
                    cls._create_log_file(state["sequence"])
                    cls._rotate_files()

                active_file = cls._file_path(state["sequence"])
                if not active_file.exists():
                    cls._create_log_file(state["sequence"])

                cls._append_row(active_file, dict(row))
                state["last_id"] = int(row["id"])
                state["records"] += 1
                state["file_size"] = active_file.stat().st_size

            if rows:
                cls._save_state(state)
            return len(rows)
        except BackupError:
            raise
        except (
            OSError,
            ValueError,
            csv.Error,
            sqlite3.Error,
            json.JSONDecodeError,
        ) as error:
            raise BackupError(
                f"Não foi possível atualizar os arquivos de log: {error}"
            ) from error

    @classmethod
    def export(cls, destination: str | Path) -> Path:
        destination_path = Path(destination)
        temporary_path = destination_path.with_suffix(
            f"{destination_path.suffix}.temporary"
        )

        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            cls.sync()
            cls._ensure_log_file()

            temporary_path.unlink(missing_ok=True)
            with zipfile.ZipFile(
                temporary_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                for log_file in cls._log_files():
                    archive.write(log_file, arcname=log_file.name)

            with zipfile.ZipFile(temporary_path, mode="r") as verification:
                if verification.testzip() is not None:
                    raise BackupError(
                        "A verificação de integridade do arquivo de logs falhou."
                    )

            temporary_path.replace(destination_path)
            return destination_path
        except BackupError:
            temporary_path.unlink(missing_ok=True)
            raise
        except (OSError, csv.Error, sqlite3.Error, zipfile.BadZipFile) as error:
            temporary_path.unlink(missing_ok=True)
            raise BackupError(
                f"Não foi possível exportar os logs: {error}"
            ) from error

    @classmethod
    def reset(cls) -> None:
        cls._ensure_directory()
        for log_file in cls._log_files():
            log_file.unlink(missing_ok=True)
        cls.STATE_PATH.unlink(missing_ok=True)

    @classmethod
    def _load_state(cls) -> dict:
        if cls.STATE_PATH.exists():
            try:
                state = json.loads(cls.STATE_PATH.read_text(encoding="utf-8"))
                sequence = int(state["sequence"])
                records = int(state["records"])
                last_id = int(state["last_id"])
                file_size = int(state["file_size"])
                active_file = cls._file_path(sequence)

                if (
                    sequence >= 1
                    and 0 <= records <= cls.MAX_RECORDS_PER_FILE
                    and last_id >= 0
                    and active_file.exists()
                    and active_file.stat().st_size == file_size
                ):
                    return {
                        "sequence": sequence,
                        "records": records,
                        "last_id": last_id,
                        "file_size": file_size,
                    }
            except (
                KeyError,
                TypeError,
                ValueError,
                OSError,
                json.JSONDecodeError,
            ):
                pass

        return cls._rebuild_state()

    @classmethod
    def _rebuild_state(cls) -> dict:
        files = cls._log_files()
        if not files:
            active_file = cls._create_log_file(1)
            state = {
                "sequence": 1,
                "records": 0,
                "last_id": 0,
                "file_size": active_file.stat().st_size,
            }
            cls._save_state(state)
            return state

        active_file = files[-1]
        sequence = cls._sequence(active_file)
        records, last_id = cls._inspect_log_file(active_file)

        # Um arquivo novo pode existir apenas com o cabeçalho caso o programa
        # seja encerrado entre a rotação e a primeira gravação. Nesse caso,
        # recupera o último ID do arquivo anterior para impedir duplicação.
        if last_id == 0:
            for previous_file in reversed(files[:-1]):
                _, previous_last_id = cls._inspect_log_file(previous_file)
                if previous_last_id:
                    last_id = previous_last_id
                    break

        state = {
            "sequence": sequence,
            "records": records,
            "last_id": last_id,
            "file_size": active_file.stat().st_size,
        }
        cls._save_state(state)
        return state

    @staticmethod
    def _inspect_log_file(path: Path) -> tuple[int, int]:
        records = 0
        last_id = 0
        with path.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.reader(file, delimiter=";")
            next(reader, None)
            for row in reader:
                records += 1
                if row and row[0].isdigit():
                    last_id = int(row[0])
        return records, last_id

    @classmethod
    def _save_state(cls, state: dict) -> None:
        temporary_path = cls.STATE_PATH.with_suffix(".temporary")
        temporary_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(cls.STATE_PATH)

    @classmethod
    def _append_row(cls, path: Path, movement: dict) -> None:
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
        with path.open("a", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(values)

    @classmethod
    def _ensure_directory(cls) -> None:
        ensure_directories()
        cls.LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _ensure_log_file(cls) -> None:
        if not cls._log_files():
            cls._create_log_file(1)
            cls.STATE_PATH.unlink(missing_ok=True)
            cls._load_state()

    @classmethod
    def _create_log_file(cls, sequence: int) -> Path:
        cls._ensure_directory()
        path = cls._file_path(sequence)
        with path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(cls.HEADERS)
        return path

    @classmethod
    def _log_files(cls) -> list[Path]:
        cls._ensure_directory()
        return sorted(
            cls.LOG_DIRECTORY.glob(f"{cls.LOG_PREFIX}*.csv"),
            key=cls._sequence,
        )

    @classmethod
    def _file_path(cls, sequence: int) -> Path:
        return cls.LOG_DIRECTORY / f"{cls.LOG_PREFIX}{sequence:06d}.csv"

    @classmethod
    def _sequence(cls, path: Path) -> int:
        try:
            return int(path.stem.removeprefix(cls.LOG_PREFIX))
        except ValueError:
            return 0

    @classmethod
    def _rotate_files(cls) -> None:
        files = cls._log_files()
        excess = len(files) - cls.MAX_LOG_FILES
        for old_file in files[:max(excess, 0)]:
            old_file.unlink(missing_ok=True)

    @staticmethod
    def default_filename() -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"SCOM_logs_movimentacoes_{timestamp}.zip"
