use crate::services;
use serde_json::Value;
use std::{
    collections::HashMap,
    io::{Read, Write},
    process::{Child, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::Duration,
};

pub type Registry = Arc<Mutex<HashMap<String, Arc<Mutex<Child>>>>>;
#[derive(Default)]
pub struct Jobs(pub Registry);
impl Drop for Jobs {
    fn drop(&mut self) {
        if let Ok(jobs) = self.0.lock() {
            for child in jobs.values() {
                if let Ok(mut child) = child.lock() {
                    let _ = child.kill();
                    let _ = child.wait();
                }
            }
        }
    }
}
pub fn ask(registry: Registry, id: String, source: String) -> Result<Value, String> {
    let mut child = services::python_command()
        .current_dir(services::project_root())
        .args(["-m", "miezee.backend.cli", "chat"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| e.to_string())?;
    let mut input = child.stdin.take().ok_or("stdin no disponible")?;
    let mut stdout = child.stdout.take().ok_or("stdout no disponible")?;
    let mut stderr = child.stderr.take().ok_or("stderr no disponible")?;
    let child = Arc::new(Mutex::new(child));
    registry
        .lock()
        .map_err(|e| e.to_string())?
        .insert(id.clone(), child.clone());
    if let Err(error) = input.write_all(source.as_bytes()) {
        if let Ok(mut child) = child.lock() {
            let _ = child.kill();
            let _ = child.wait();
        }
        registry.lock().map_err(|e| e.to_string())?.remove(&id);
        return Err(error.to_string());
    }
    drop(input);
    let out = thread::spawn(move || {
        let mut bytes = Vec::new();
        let _ = stdout.read_to_end(&mut bytes);
        bytes
    });
    let err = thread::spawn(move || {
        let mut bytes = Vec::new();
        let _ = stderr.read_to_end(&mut bytes);
        bytes
    });
    let status = loop {
        if let Some(status) = child
            .lock()
            .map_err(|e| e.to_string())?
            .try_wait()
            .map_err(|e| e.to_string())?
        {
            break status;
        }
        thread::sleep(Duration::from_millis(40));
    };
    registry.lock().map_err(|e| e.to_string())?.remove(&id);
    let output = out.join().map_err(|_| "No se pudo leer la respuesta")?;
    let errors = err.join().map_err(|_| "No se pudo leer stderr")?;
    if !status.success() {
        return Err(String::from_utf8_lossy(&errors).into_owned());
    }
    serde_json::from_slice(&output).map_err(|e| e.to_string())
}
#[tauri::command]
pub fn cancel_chat(state: tauri::State<'_, Jobs>, request_id: String) -> Result<(), String> {
    if let Some(child) = state.0.lock().map_err(|e| e.to_string())?.get(&request_id) {
        child
            .lock()
            .map_err(|e| e.to_string())?
            .kill()
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}
