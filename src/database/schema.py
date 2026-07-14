from src.database.connection import database_connection


SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    requires_component_value INTEGER NOT NULL DEFAULT 0,
    value_label TEXT,
    default_unit TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    category_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT,
    internal_code TEXT NOT NULL COLLATE NOCASE UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    category_id INTEGER NOT NULL,
    component_value TEXT,
    component_unit TEXT,
    model_id INTEGER,
    current_quantity INTEGER NOT NULL DEFAULT 0 CHECK (current_quantity >= 0),
    minimum_quantity INTEGER NOT NULL DEFAULT 1 CHECK (minimum_quantity >= 0),
    physical_location TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (model_id) REFERENCES models(id)
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL CHECK (movement_type IN ('ENTRADA', 'SAÍDA')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    previous_quantity INTEGER NOT NULL,
    resulting_quantity INTEGER NOT NULL CHECK (resulting_quantity >= 0),
    reason TEXT NOT NULL,
    responsible TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (part_id) REFERENCES parts(id)
);

CREATE INDEX IF NOT EXISTS idx_parts_internal_code ON parts(internal_code);
CREATE INDEX IF NOT EXISTS idx_parts_name ON parts(name);
CREATE INDEX IF NOT EXISTS idx_parts_location ON parts(physical_location);
CREATE INDEX IF NOT EXISTS idx_parts_category_id ON parts(category_id);
CREATE INDEX IF NOT EXISTS idx_parts_model_id ON parts(model_id);
CREATE INDEX IF NOT EXISTS idx_parts_current_quantity ON parts(current_quantity);
CREATE INDEX IF NOT EXISTS idx_parts_component_value ON parts(component_value);
CREATE INDEX IF NOT EXISTS idx_models_category_id ON models(category_id);
CREATE INDEX IF NOT EXISTS idx_movements_part_id ON stock_movements(part_id);
CREATE INDEX IF NOT EXISTS idx_movements_type ON stock_movements(movement_type);
CREATE INDEX IF NOT EXISTS idx_movements_created_at ON stock_movements(created_at);
"""

DEFAULT_CATEGORIES = (
    ("Resistor", 1, "Valor da resistência", "Ω"),
    ("Capacitor", 1, "Capacitância", "F"),
    ("Diodo", 1, "Valor ou referência do diodo", ""),
    ("Transistor", 0, "", ""),
    ("Circuito integrado", 0, "", ""),
    ("Conector", 0, "", ""),
    ("Relé", 1, "Tensão da bobina", "V"),
    ("Fusível", 1, "Corrente nominal", "A"),
    ("Ferramenta", 0, "", ""),
    ("Outros", 0, "", ""),
)


def initialize_database() -> None:
    with database_connection() as connection:
        connection.executescript(SCHEMA)
        connection.executemany(
            """
            INSERT OR IGNORE INTO categories
                (name, requires_component_value, value_label, default_unit)
            VALUES (?, ?, ?, ?)
            """,
            DEFAULT_CATEGORIES,
        )
