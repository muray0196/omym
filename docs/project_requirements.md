# OMYM PRD (Project Requirements Document)

### 1. Overview

Organize My Music (OMYM) is a desktop tool designed to organize music libraries.  
Based on audio file metadata, it automatically renames music files and creates and maintains a consistently structured, organized music library.  
This allows users to manage their music collections more easily.

---

### 2. Functional Requirements

#### 2.1 Core Features

- **Metadata Extraction**  
When creating each folder and renaming each file, extract the required metadata from the audio files.

- **Track File Renaming**  
Rename track files based on the track number, track name, disc number, and artist name extracted from the track metadata.

- **Music Library Structuring**
To organize all music files in the target music library, create folders and move music files accordingly.

- **Artist Tag Generation**
For each track file, generate a "artist tag" up to 5-character based on the artist name after applying transliteration and simplification.

- **Name Sanitization**  
  - For readability and cross-platform compatibility, sanitize all folder and file names.
  - Apply steps such as removing apostrophes, replacing prohibited characters with hyphens, compressing consecutive hyphens into one, and removing hyphens at the start or end of the name.

---

#### 2.2 User Interface

- **Command-Line Interface (CLI)**  
  - Provide simple command-line options.
  - Execute the program by specifying the base path as an argument.
  - Optionally, users can specify separate target paths for processing folders and music library folders.

- **Graphical User Interface (GUI)**  
  - Provide a user-friendly GUI built with Tkinter.
  - Allow the user to select the base path of the music library.
  - Offer checkboxes to select various operations such as "Track File Renaming," "Structuring," and "Sanitization."
  - Include a text widget in the GUI to display critical logs such as start, end, and error messages.

- **Logging**  
  - The system records all operations and errors in a log file.
  - The path of the log file can be set in a log folder.
  - Logs include timestamps, log levels (INFO, WARNING, ERROR), and detailed messages.

---

#### 2.3 Configuration

- **Configuration File**
  - The system saves various settings (including the log file path and the last-used base path) in a JSON configuration file.
  - The configuration file is loaded at startup and saved when changes occur.

---

#### 2.4 Database Utilization

- **Managing Pre-Processing and Post-Processing Databases**  
  - The system uses databases (DB) to handle the "Plan," "Review," and "Execute" phases of the music file organization process.  
  - After an initial large-scale processing, using both pre- and post-processing DBs makes it possible to handle only newly added files in a differential manner, reducing the need for re-scanning and re-calculating all files.  
  - When files are added, deleted, or changed, the pre-processing DB is synchronized with the file system, and only the necessary differences are reflected in the post-processing DB, reducing processing time and effort.

- **Using the Artist ID Cache Table**  
  - Introduce an `artist_cache` table (for example) to store pairs of (original artist name, generated ID).
  - When an ID generation request is made, the system first checks the DB cache and returns immediately if there is a hit.  
  - If not found in the cache, the system uses polyglot to generate the ID, then stores it in the DB.  
  - This greatly improves performance when the same artist name appears in multiple files.

---

### 3. Non-Functional Requirements

#### 3.1 Performance

- The system must efficiently handle large music libraries.
- Use multithreading to improve track file processing speed.

#### 3.2 Usability

- The CLI is simple and intended for skilled users.
- The GUI is designed to be intuitive and easy to use for users with varying technical skills.

#### 3.3 Portability

- The system is compatible with major operating systems (Windows, macOS, Linux).
- The system processes file paths in a platform-independent manner.

---