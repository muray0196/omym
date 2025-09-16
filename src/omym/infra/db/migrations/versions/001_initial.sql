-- Drop old tables
DROP TABLE IF EXISTS path_components;

-- Update processing_before table
DROP TABLE IF EXISTS processing_before;
CREATE TABLE processing_before (
    file_hash TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    title TEXT,
    artist TEXT,
    album TEXT,
    album_artist TEXT,
    genre TEXT,
    year INTEGER,
    track_number INTEGER,
    track_total INTEGER,
    disc_number INTEGER,
    disc_total INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_path),
    UNIQUE (file_hash)
);

-- Update processing_after table
DROP TABLE IF EXISTS processing_after;
CREATE TABLE processing_after (
    file_hash TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    target_path TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_path),
    FOREIGN KEY (file_path) REFERENCES processing_before (file_path),
    FOREIGN KEY (file_hash) REFERENCES processing_before (file_hash)
);

-- Create albums table
DROP TABLE IF EXISTS albums;
CREATE TABLE albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    album_name TEXT NOT NULL,
    album_artist TEXT NOT NULL,
    year INTEGER,
    track_total INTEGER,
    disc_total INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (album_name, album_artist)
);

-- Create track_positions table
DROP TABLE IF EXISTS track_positions;
CREATE TABLE track_positions (
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

-- Create filter_hierarchies table
DROP TABLE IF EXISTS filter_hierarchies;
CREATE TABLE filter_hierarchies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    priority INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name)
);

-- Create filter_values table
DROP TABLE IF EXISTS filter_values;
CREATE TABLE filter_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hierarchy_id INTEGER NOT NULL,
    file_hash TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hierarchy_id) REFERENCES filter_hierarchies (id),
    FOREIGN KEY (file_hash) REFERENCES processing_before (file_hash)
);

-- Create artist_cache table
DROP TABLE IF EXISTS artist_cache;
CREATE TABLE artist_cache (
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
