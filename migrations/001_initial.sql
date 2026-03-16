CREATE TABLE IF NOT EXISTS printers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    serial_number TEXT,
    model TEXT,
    access_code TEXT,
    mqtt_username TEXT NOT NULL DEFAULT 'elegoo',
    mqtt_password TEXT,
    token_status INTEGER,
    lan_status INTEGER,
    camera_url TEXT,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    last_connect_ok_at TEXT,
    last_connect_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS printer_state (
    printer_id INTEGER PRIMARY KEY,
    is_online INTEGER NOT NULL DEFAULT 0,
    status TEXT,
    sub_status TEXT,
    current_file TEXT,
    progress REAL,
    layer_current INTEGER,
    layer_total INTEGER,
    nozzle_temp REAL,
    nozzle_target REAL,
    bed_temp REAL,
    bed_target REAL,
    chamber_temp REAL,
    print_speed REAL,
    fan_speed REAL,
    elapsed_seconds INTEGER,
    remaining_seconds INTEGER,
    z_offset REAL,
    raw_status_json TEXT,
    last_message_at TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(printer_id) REFERENCES printers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS printer_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    printer_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    message TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(printer_id) REFERENCES printers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS discovered_printers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    serial_number TEXT,
    model TEXT,
    host_name TEXT,
    token_status INTEGER,
    lan_status INTEGER,
    discovered_at TEXT NOT NULL
);
