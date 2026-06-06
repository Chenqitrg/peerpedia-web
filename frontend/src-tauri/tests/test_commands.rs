// Integration tests — verify the full pipeline from IPC command → SQLite → response.
// These tests exercise the same code paths that Tauri invoke() calls use at runtime.
//
// Note: These tests compile the crate as a library, so they use `peerpedia::*` imports.
// The main.rs binary is not testable directly; commands are tested through their
// public function signatures.

use peerpedia::commands;
use peerpedia::db::init_db;
use peerpedia::AppState;
use std::sync::Mutex;

fn test_state() -> AppState {
    let conn = init_db().unwrap();
    AppState {
        db: Mutex::new(conn),
    }
}

// We can't easily test Tauri commands directly without the Tauri runtime, but we
// can test the underlying module functions through the same call chain.
// For full E2E: run `cargo test` with a Tauri test harness (requires binary).
//
// These tests validate that all modules link correctly and basic flows work.

#[test]
fn test_full_account_flow() {
    let state = test_state();
    let conn = state.db.lock().unwrap();

    // Create account
    let account = peerpedia::local_auth::create_account(&conn, "testuser", "password123", "test@test.com", "Test User").unwrap();
    assert_eq!(account.username, "testuser");

    // Login
    let logged = peerpedia::local_auth::login(&conn, "testuser", "password123").unwrap();
    assert_eq!(logged.id, account.id);

    // List
    let accounts = peerpedia::local_auth::list_accounts(&conn).unwrap();
    assert_eq!(accounts.len(), 1);
}

#[test]
fn test_full_draft_flow() {
    let state = test_state();
    let conn = state.db.lock().unwrap();

    // Create account first
    peerpedia::local_auth::create_account(&conn, "writer", "pass", "", "Writer").unwrap();

    // Save draft
    let draft = peerpedia::local_store::save_draft(&conn, None, "writer", "My Draft", "# Hello", "markdown").unwrap();
    assert_eq!(draft.title, "My Draft");

    // Update
    let updated = peerpedia::local_store::save_draft(&conn, Some(&draft.id), "writer", "Updated", "new", "markdown").unwrap();
    assert_eq!(updated.title, "Updated");

    // List
    let drafts = peerpedia::local_store::list_drafts(&conn, "writer").unwrap();
    assert_eq!(drafts.len(), 1);

    // Delete
    peerpedia::local_store::delete_draft(&conn, &draft.id).unwrap();
    let result = peerpedia::local_store::get_draft(&conn, &draft.id);
    assert!(result.is_err());
}

#[test]
fn test_full_cache_flow() {
    let state = test_state();
    let conn = state.db.lock().unwrap();

    // Cache article
    peerpedia::local_store::cache_article(&conn, "art-1", r#"{"title":"Test Article","score":{"O":4,"R":3}}"#).unwrap();

    // Retrieve
    let cached = peerpedia::local_store::get_cached_article(&conn, "art-1").unwrap().unwrap();
    assert_eq!(cached.id, "art-1");
    assert!(cached.json.contains("Test Article"));

    // Overwrite
    peerpedia::local_store::cache_article(&conn, "art-1", r#"{"title":"Updated"}"#).unwrap();
    let updated = peerpedia::local_store::get_cached_article(&conn, "art-1").unwrap().unwrap();
    assert!(updated.json.contains("Updated"));

    // Not found
    let missing = peerpedia::local_store::get_cached_article(&conn, "nonexistent").unwrap();
    assert!(missing.is_none());
}
