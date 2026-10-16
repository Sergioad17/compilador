use crate::{jobs, services};
use serde_json::Value;

#[tauri::command]
pub async fn python_request(
    state: tauri::State<'_, jobs::Jobs>,
    operation: String,
    source: String,
    request_id: Option<String>,
) -> Result<Value, String> {
    if !["analyze", "translate", "chat", "status", "settings"].contains(&operation.as_str()) {
        return Err("Operacion no disponible".into());
    }
    if operation == "chat" {
        let registry = state.0.clone();
        let id = request_id.ok_or("Solicitud de chat sin identificador")?;
        return tauri::async_runtime::spawn_blocking(move || jobs::ask(registry, id, source))
            .await
            .map_err(|e| e.to_string())?;
    }
    tauri::async_runtime::spawn_blocking(move || services::python(&operation, &source))
        .await
        .map_err(|error| error.to_string())?
}

#[tauri::command]
pub async fn list_examples() -> Result<Value, String> {
    tauri::async_runtime::spawn_blocking(services::examples)
        .await
        .map_err(|error| error.to_string())?
}
