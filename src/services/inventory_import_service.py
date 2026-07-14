import shutil
import sqlite3
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from src.database.connection import database_connection
from src.database.schema import initialize_database
from src.services.backup_service import BackupError, BackupService
from src.services.movement_log_service import MovementLogService
from src.utils.paths import DATABASE_PATH, ensure_directories


class InventoryImportService:
    @classmethod
    def import_inventory(cls, source: str | Path) -> dict:
        source_path = Path(source)
        if not source_path.exists() or not source_path.is_file():
            raise BackupError("O arquivo selecionado não existe.")
        if source_path.suffix.lower() not in {".db", ".zip"}:
            raise BackupError("Selecione um arquivo de backup .db ou .zip.")

        ensure_directories()
        safety_backup: Path | None = None
        copied_photos = 0
        logs_rebuilt = True

        try:
            with TemporaryDirectory(prefix="scom_import_") as temporary_directory:
                temporary_root = Path(temporary_directory)
                photos_root: Path | None = None

                if source_path.suffix.lower() == ".zip":
                    BackupService._safe_extract_zip(source_path, temporary_root)
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

                BackupService._validate_database(imported_database)

                # A cópia do inventário atual é concluída antes de qualquer
                # conteúdo importado ser gravado nas pastas locais.
                safety_backup = BackupService._create_safety_backup()

                copied_photos = BackupService._normalize_imported_photos(
                    imported_database,
                    photos_root,
                )
                BackupService._validate_database(imported_database)

                importing_path = DATABASE_PATH.with_suffix(".db.importing")
                importing_path.unlink(missing_ok=True)
                shutil.copy2(imported_database, importing_path)
                BackupService._validate_database(importing_path)
                importing_path.replace(DATABASE_PATH)

            # Cria índices e componentes compatíveis com a versão atual sem
            # remover ou sobrescrever os registros restaurados.
            initialize_database()

            try:
                MovementLogService.reset()
                MovementLogService.sync()
            except (BackupError, OSError):
                # O SQLite importado permanece como fonte completa do histórico.
                # Os CSVs podem ser reconstruídos em uma exportação posterior.
                logs_rebuilt = False

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
            "logs_rebuilt": logs_rebuilt,
        }
