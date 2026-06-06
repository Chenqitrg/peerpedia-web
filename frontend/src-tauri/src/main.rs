// PeerPedia Tauri Desktop — entry point
// Registers IPC commands and initializes the local SQLite database.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod db;
mod error;
mod local_auth;
mod local_store;

use db::init_db;
use std::sync::Mutex;
use rusqlite::Connection;

/// Shared database connection, protected by a Mutex for thread safety.
pub struct AppState {
    pub db: Mutex<Connection>,
}

fn main() {
    let conn = init_db().expect("Failed to initialize database");
    let state = AppState {
        db: Mutex::new(conn),
    };

    tauri::Builder::default()
        .manage(state)
        .invoke_handler(tauri::generate_handler![
            commands::create_account,
            commands::login,
            commands::list_accounts,
            commands::save_draft,
            commands::list_drafts,
            commands::get_draft,
            commands::delete_draft,
            commands::cache_article,
            commands::get_cached_article,
        ])
        .run(tauri::generate_context!())
        .expect("error while running PeerPedia");
}
