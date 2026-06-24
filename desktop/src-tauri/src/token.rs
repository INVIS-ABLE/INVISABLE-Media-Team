//! Server-issued API token storage in the OS keychain.
//!
//! The desktop app authenticates to the server API with a bearer token. It is kept
//! in OS-safe storage (Windows Credential Manager / macOS Keychain / Secret Service)
//! — never in the frontend, never in the settings JSON. The frontend can only ask
//! "is a token set?" and trigger save/clear; it never reads the secret back.

use keyring::Entry;

const SERVICE: &str = "uk.co.invisable.media.desktop";
const ACCOUNT: &str = "api-token";

fn entry() -> Result<Entry, String> {
    Entry::new(SERVICE, ACCOUNT).map_err(|e| format!("keychain unavailable: {e}"))
}

/// Store (or replace) the API token.
pub fn set(token: &str) -> Result<(), String> {
    entry()?
        .set_password(token)
        .map_err(|e| format!("store token: {e}"))
}

/// Read the token for internal use (attaching to requests). Not exposed to the UI.
pub fn get() -> Option<String> {
    entry().ok().and_then(|e| e.get_password().ok())
}

/// Whether a token is currently stored.
pub fn exists() -> bool {
    get().is_some()
}

/// Remove the stored token (logout).
pub fn clear() -> Result<(), String> {
    match entry()?.delete_credential() {
        Ok(()) => Ok(()),
        // Treat "nothing stored" as success — logout is idempotent.
        Err(keyring::Error::NoEntry) => Ok(()),
        Err(e) => Err(format!("clear token: {e}")),
    }
}
