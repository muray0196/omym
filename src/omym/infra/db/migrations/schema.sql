-- Schema for the OMYM database

-- Table: processing_before
CREATE TABLE IF NOT EXISTS processing_before (
    file_hash TEXT PRIMARY KEY,
    file_path TEXT NOT NULL UNIQUE,
    title TEXT,
    artist TEXT,
    album TEXT,
    album_artist TEXT,
    genre TEXT,
    year INTEGER,
    track_number INTEGER,
    total_tracks INTEGER,
    disc_number INTEGER,
    total_discs INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table: processing_after
CREATE TABLE IF NOT EXISTS processing_after (
    file_hash TEXT PRIMARY KEY,
    file_path TEXT NOT NULL UNIQUE,
    target_path TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_hash) REFERENCES processing_before (file_hash)
);

-- Table: albums
CREATE TABLE IF NOT EXISTS albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    album_name TEXT NOT NULL,
    album_artist TEXT NOT NULL,
    year INTEGER,
    total_tracks INTEGER,
    total_discs INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (album_name, album_artist)
);

-- Table: track_positions
CREATE TABLE IF NOT EXISTS track_positions (
    album_id INTEGER NOT NULL,
    disc_number INTEGER NOT NULL,
    track_number INTEGER NOT NULL,
    file_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (album_id, disc_number, track_number),
    FOREIGN KEY (album_id) REFERENCES albums (id),
    FOREIGN KEY (file_hash) REFERENCES processing_before (file_hash)
);

-- Table: filter_hierarchies
CREATE TABLE IF NOT EXISTS filter_hierarchies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    priority INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name)
);

-- Table: filter_values
CREATE TABLE IF NOT EXISTS filter_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hierarchy_id INTEGER NOT NULL,
    file_hash TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hierarchy_id) REFERENCES filter_hierarchies (id),
    FOREIGN KEY (file_hash) REFERENCES processing_before (file_hash)
);

-- Table: artist_cache
CREATE TABLE IF NOT EXISTS artist_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artist_name TEXT NOT NULL,
    artist_id TEXT NOT NULL,
    romanized_name TEXT,
    romanization_source TEXT,
    romanized_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (artist_name)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_albums_name_artist ON albums(album_name, album_artist);
CREATE INDEX IF NOT EXISTS idx_track_positions_file_hash ON track_positions(file_hash);
CREATE INDEX IF NOT EXISTS idx_filter_values_file_hash ON filter_values(file_hash);
CREATE INDEX IF NOT EXISTS idx_filter_values_hierarchy ON filter_values(hierarchy_id);
CREATE INDEX IF NOT EXISTS idx_artist_cache_name ON artist_cache(artist_name); 
