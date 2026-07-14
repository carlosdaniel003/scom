import csv
import shutil
import sqlite3
import zipfile
from contextlib import closing
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.database.connection import database_connection
from src.utils.paths import (
    DATA_DIR,
    DATABASE_PATH,
    PROJECT_ROOT,
    UPLOAD_DIR,
    ensure_directories,
)


class BackupError(RuntimeError):
    pass


class BackupService:
    MAX_LOG_FILES = 10
    MAX_RECORDS_PER_FILE = 10_000
    MAX_SAFETY_BACKUPS = 5
    LOG_DIRECTORY = DATA_DIR / "movement_logs"
    SAFETY_BACKUP_DIRECTORY = DATA_DIR / "import_safety_backups"
    LOG_PREFIX = "movimentacoes_"

    INVENTORY_HEADERS = (
        "Código interno",
        "Peça",
        "Descrição",
        "Categoria",
        "Valor técnico",
        "Unidade",
        "Modelo",
        "Quantidade física",
        "Quantidade mínima",
        "Localização física",
        "Status",
        "Foto no backup",
        "Observações",
        "Criado em",
        "Atualizado em",
    )

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

    REQUIRED_DATABASE_COLUMNS = {
        "categories": {"id", "name", "requires_component_value"},
        "models": {"id", "name", "category_id"},
        "parts": {
            "id",
            "internal_code",
            "name",
            "category_id",
            "current_quantity",
            "minimum_quantity",
            "physical_location",
            "image_path",
        },
        "stock_movements": {
            "id",
            "part_id",
            "movement_type",
            "quantity",
            "previous_quantity",
            "resulting_quantity",
            "reason",
            "responsible",
            "created_at",
        },
    }

    @staticmethod
    def backup_database(destination: str | Path) -> Path:
        destination_path = Path(destination)
        temporary_path = destination_path.with_suffix(
            f"{destination_path.suffix}.temporary"
        )

        try:
            ensure_directories()
            destination_path.parent.mkdir(parents=True, exist_ok=True)

            if destination_path.resolve() == DATABASE_PATH.resolve():
                raise BackupError(
                    "Escolha um local diferente do banco de dados em uso."
                )

            temporary_path.unlink(missing_ok=True)
            with closing(sqlite3.connect(DATABASE_PATH)) as source:
                with closing(sqlite3.connect(temporary_path)) as target:
                    source.backup(target)

            BackupService._validate_database(temporary_path)
            temporary_path.replace(destination_path)
        except BackupError:
            temporary_path.unlink(missing_ok=True)
            raise
        except (OSError, sqlite3.Error) as error:
            temporary_path.unlink(missing_ok=True)
            raise BackupError(f"Não foi possível criar o backup: {error}") from error

        return destination_path

    @classmethod
    def export_inventory_backup(cls, destination: str | Path) -> Path:
        destination_path = Path(destination)
        temporary_archive = destination_path.with_suffix(
            f"{destination_path.suffix}.temporary"
        )

        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_archive.unlink(missing_ok=True)

            with TemporaryDirectory(prefix="scom_backup_") as temporary_directory:
                temporary_root = Path(temporary_directory)
                database_copy = temporary_root / "SCOM_inventario.db"
                inventory_csv = temporary_root / "SCOM_inventario.csv"
                photos_directory = temporary_root / "photos"

                cls.backup_database(database_copy)
                cls._prepare_backup_photos(database_copy, photos_directory)
                cls._export_inventory_csv(database_copy, inventory_csv)

                with zipfile.ZipFile(
                    temporary_archive,
                    mode="w",
                    compression=zipfile.ZIP_DEFLATED,
                ) as archive:
                    archive.write(database_copy, arcname=database_copy.name)
                    archive.write(inventory_csv, arcname=inventory_csv.name)
                    if photos_directory.exists():
                        for photo in photos_directory.rglob("*"):
                            if photo.is_file():
                                archive.write(
                                    photo,
                                    arcname=photo.relative_to(temporary_root).as_posix(),
                                )

            with zipfile.ZipFile(temporary_archive, mode="r") as verification:
                required_files = {"SCOM_inventario.db", "SCOM_inventario.csv"}
                if not required_files.issubset(set(verification.namelist())):
                    raise BackupError(
                        "O pacote de backup não contém os arquivos obrigatórios."
                    )
                if verification.testzip() is not None:
                    raise BackupError(
                        "A verificação de integridade do pacote de backup falhou."
                    )

            temporary_archive.replace(destination_path)
        except BackupError:
            temporary_archive.unlink(missing_ok=True)
            raise
        except (OSError, csv.Error, sqlite3.Error, zipfile.BadZipFile) as error:
            temporary_archive.unlink(missing_ok=True)
            raise BackupError(
                f"Não foi possível exportar o inventário: {error}"
            ) from error

        return destination_path

    @classmethod
    def import_inventory(cls, source: str | Path) -> dict:
        source_path = Path(source)
        if not source_path.exists() or not source_path.is_file():
            raise BackupError("O arquivo selecionado não existe.")
        if source_path.suffix.lower() not in {".db", ".zip"}:
            raise BackupError("Selecione um arquivo de backup .db ou .zip.")

        ensure_directories()

        try:
            with TemporaryDirectory(prefix="scom_import_") as temporary_directory:
                temporary_root = Path(temporary_directory)
                photos_root: Path | None = None

                if source_path.suffix.lower() == ".zip":
                    cls._safe_extract_zip(source_path, temporary_root)
                    database_candidates = list(temporary_root.rglob("*.db"))
                    if len(database_candidates) != 1:
                        raise BackupError(
                            "O ZIP deve conter exatamente um banco de dados .db."
                        )
                    imported_database = database_candidates[0]
                    photos_root = temporary_root / "photos"
                else:
                    imported_database = temporary_root / "SCOM_importado.db"
                    shutil.copy2(source_path, imported_database)

                cls._validate_database(imported_database)
                copied_photos = cls._normalize_imported_photos(
                    imported_database,
                    photos_root,
                )
                cls._validate_database(imported_database)

                safety_backup = cls._create_safety_backup()
                importing_path = DATABASE_PATH.with_suffix(".db.importing")
                importing_path.unlink(missing_ok=True)
                shutil.copy2(imported_database, importing_path)
                cls._validate_database(importing_path)
                importing_path.replace(DATABASE_PATH)

            for log_file in cls._log_files():
                log_file.unlink(missing_ok=True)
            cls.sync_movement_logs()

            with database_connection() as connection:
                part_count = int(
                    connection.execute(
                        "SELECT COUNT(*) AS total FROM parts"
                    ).fetchone()["total"]
                )
                movement_count = int(
                    connection.execute(
                        "SELECT COUNT(*) AS total FROM stock_movements"
                    ).fetchone()["total"]
                )
        except BackupError:
            raise
        except (OSError, sqlite3.Error, zipfile.BadZipFile) as error:
            raise BackupError(
                f"Não foi possível importar o inventário: {error}"
            ) from error

        return {
            "parts": part_count,
            "movements": movement_count,
            "photos": copied_photos,
            "safety_backup": safety_backup,
        }

    @classmethod
    def _prepare_backup_photos(
        cls,
        database_path: str | Path,
        photos_directory: Path,
    ) -> int:
        copied_count = 0
        with closing(sqlite3.connect(database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, image_path
                FROM parts
                WHERE TRIM(COALESCE(image_path, '')) <> ''
                ORDER BY id
                """
            ).fetchall()

            for row in rows:
                source = cls._resolve_existing_image(row["image_path"])
                if source is None:
                    connection.execute(
                        "UPDATE parts SET image_path = NULL WHERE id = ?",
                        (row["id"],),
                    )
                    continue

                photos_directory.mkdir(parents=True, exist_ok=True)
                destination_name = f"{row['id']}_{source.name}"
                destination = photos_directory / destination_name
                shutil.copy2(source, destination)
                relative_path = Path("photos", destination_name).as_posix()
                connection.execute(
                    "UPDATE parts SET image_path = ? WHERE id = ?",
                    (relative_path, row["id"]),
                )
                copied_count += 1

            connection.commit()
        return copied_count

    @staticmethod
    def _resolve_existing_image(image_path: str | None) -> Path | None:
        if not image_path:
            return None

        path = Path(image_path)
        candidates = [path]
        if not path.is_absolute():
            candidates.append(PROJECT_ROOT / path)
            candidates.append(UPLOAD_DIR / path.name)

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    @classmethod
    def _normalize_imported_photos(
        cls,
        database_path: Path,
        photos_root: Path | None,
    ) -> int:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        copied_count = 0

        with closing(sqlite3.connect(database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT id, image_path
                FROM parts
                WHERE TRIM(COALESCE(image_path, '')) <> ''
                """
            ).fetchall()

            for row in rows:
                stored_path = str(row["image_path"] or "")
                source: Path | None = None

                if photos_root and photos_root.exists():
                    relative_candidate = photos_root.parent / stored_path
                    basename_candidate = photos_root / Path(stored_path).name
                    for candidate in (relative_candidate, basename_candidate):
                        if candidate.exists() and candidate.is_file():
                            source = candidate
                            break

                if source is None:
                    source = cls._resolve_existing_image(stored_path)

                if source is None:
                    connection.execute(
                        "UPDATE parts SET image_path = NULL WHERE id = ?",
                        (row["id"],),
                    )
                    continue

                destination = UPLOAD_DIR / source.name
                if source.resolve() != destination.resolve():
                    shutil.copy2(source, destination)
                    copied_count += 1
                connection.execute(
                    "UPDATE parts SET image_path = ? WHERE id = ?",
                    (str(destination), row["id"]),
                )

            connection.commit()

        return copied_count

    @classmethod
    def _create_safety_backup(cls) -> Path:
        cls.SAFETY_BACKUP_DIRECTORY.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        destination = (
            cls.SAFETY_BACKUP_DIRECTORY
            / f"SCOM_antes_importacao_{timestamp}.zip"
        )
        cls.export_inventory_backup(destination)

        backups = sorted(
            cls.SAFETY_BACKUP_DIRECTORY.glob("SCOM_antes_importacao_*.zip"),
            key=lambda path: path.stat().st_mtime,
        )
        excess = len(backups) - cls.MAX_SAFETY_BACKUPS
        for old_backup in backups[:max(excess, 0)]:
            old_backup.unlink(missing_ok=True)

        return destination

    @classmethod
    def _validate_database(cls, database_path: str | Path) -> None:
        path = Path(database_path)
        if not path.exists() or path.stat().st_size == 0:
            raise BackupError("O banco de dados está vazio ou não existe.")

        try:
            with closing(
                sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
            ) as connection:
                quick_check = connection.execute("PRAGMA quick_check").fetchone()
                if not quick_check or quick_check[0] != "ok":
                    raise BackupError(
                        "O banco selecionado não passou na verificação de integridade."
                    )

                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                missing_tables = set(cls.REQUIRED_DATABASE_COLUMNS) - tables
                if missing_tables:
                    raise BackupError(
                        "O arquivo não possui a estrutura completa do SCOM."
                    )

                for table, required_columns in cls.REQUIRED_DATABASE_COLUMNS.items():
                    columns = {
                        row[1]
                        for row in connection.execute(
                            f"PRAGMA table_info({table})"
                        ).fetchall()
                    }
                    if not required_columns.issubset(columns):
                        raise BackupError(
                            f"A tabela {table} não possui todos os campos necessários."
                        )
        except BackupError:
            raise
        except sqlite3.Error as error:
            raise BackupError(
                f"O arquivo selecionado não é um banco SCOM válido: {error}"
            ) from error

    @staticmethod
    def _safe_extract_zip(source: Path, destination: Path) -> None:
        with zipfile.ZipFile(source, mode="r") as archive:
            for member in archive.infolist():
                member_path = Path(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise BackupError(
                        "O arquivo ZIP contém caminhos de arquivo inválidos."
                    )
            archive.extractall(destination)

    @classmethod
    def _export_inventory_csv(
        cls,
        database_path: str | Path,
        destination: str | Path,
    ) -> Path:
        destination_path = Path(destination)

        with closing(sqlite3.connect(database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT
                    p.internal_code,
                    p.name,
                    COALESCE(p.description, '') AS description,
                    c.name AS category_name,
                    COALESCE(p.component_value, '') AS component_value,
                    COALESCE(p.component_unit, '') AS component_unit,
                    COALESCE(m.name, '') AS model_name,
                    p.current_quantity,
                    p.minimum_quantity,
                    p.physical_location,
                    CASE
                        WHEN p.current_quantity = 0 THEN 'Sem estoque'
                        WHEN p.current_quantity <= p.minimum_quantity
                            THEN 'Estoque baixo'
                        ELSE 'Disponível'
                    END AS stock_status,
                    COALESCE(p.image_path, '') AS image_path,
                    COALESCE(p.notes, '') AS notes,
                    p.created_at,
                    p.updated_at
                FROM parts p
                JOIN categories c ON c.id = p.category_id
                LEFT JOIN models m ON m.id = p.model_id
                ORDER BY c.name COLLATE NOCASE,
                         p.name COLLATE NOCASE,
                         p.internal_code COLLATE NOCASE
                """
            ).fetchall()

        with destination_path.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(cls.INVENTORY_HEADERS)
            for row in rows:
                writer.writerow(
                    (
                        row["internal_code"],
                        row["name"],
                        row["description"],
                        row["category_name"],
                        row["component_value"],
                        row["component_unit"],
                        row["model_name"] or "—",
                        row["current_quantity"],
                        row["minimum_quantity"],
                        row["physical_location"],
                        row["stock_status"],
                        row["image_path"] or "—",
                        row["notes"],
                        row["created_at"],
                        row["updated_at"],
                    )
                )

        return destination_path

    @classmethod
    def sync_movement_logs(cls) -> int:
        try:
            cls._ensure_log_directory()
            last_logged_id = cls._last_logged_id()

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

            for row in rows:
                cls._append_log_row(dict(row))
        except BackupError:
            raise
        except (OSError, csv.Error, sqlite3.Error, ValueError) as error:
            raise BackupError(
                f"Não foi possível atualizar os arquivos de log: {error}"
            ) from error

        return len(rows)

    @classmethod
    def export_movement_logs(cls, destination: str | Path) -> Path:
        destination_path = Path(destination)
        temporary_path = destination_path.with_suffix(
            f"{destination_path.suffix}.temporary"
        )

        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            cls.sync_movement_logs()
            cls._ensure_empty_log_file()

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
        except BackupError:
            temporary_path.unlink(missing_ok=True)
            raise
        except (OSError, csv.Error, sqlite3.Error, zipfile.BadZipFile) as error:
            temporary_path.unlink(missing_ok=True)
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
        for log_file in reversed(cls._log_files()):
            last_id = 0
            with log_file.open("r", newline="", encoding="utf-8-sig") as file:
                reader = csv.reader(file, delimiter=";")
                next(reader, None)
                for row in reader:
                    if row and row[0].isdigit():
                        last_id = int(row[0])
            if last_id:
                return last_id
        return 0

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
    def default_inventory_backup_filename() -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"SCOM_backup_inventario_{timestamp}.zip"

    @staticmethod
    def default_logs_filename() -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"SCOM_logs_movimentacoes_{timestamp}.zip"
