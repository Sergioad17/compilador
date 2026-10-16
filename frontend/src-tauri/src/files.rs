use crate::services;
use serde_json::{json, Value};
use std::{
    path::{Path, PathBuf},
    sync::Mutex,
};

#[derive(Default)]
pub struct Files(pub Mutex<Vec<PathBuf>>);

fn allowed(path: &Path) -> Result<(), String> {
    let resolved = path
        .canonicalize()
        .or_else(|_| {
            path.parent()
                .unwrap_or(Path::new("."))
                .canonicalize()
                .map(|p| p.join(path.file_name().unwrap_or_default()))
        })
        .map_err(|e| e.to_string())?;
    let root = services::project_root()
        .canonicalize()
        .map_err(|e| e.to_string())?;
    if resolved.starts_with(&root)
        && !resolved.starts_with(root.join("examples"))
        && !resolved.starts_with(root.join("outputs"))
    {
        return Err("El codigo fuente interno del IDE no se muestra en el explorador.".into());
    }
    Ok(())
}
fn document(path: &Path) -> Result<Value, String> {
    allowed(path)?;
    let path = &path.canonicalize().map_err(|e| e.to_string())?;
    let source = std::fs::read_to_string(path).map_err(|e| e.to_string())?;
    Ok(
        json!({"id": path.to_string_lossy(), "path": path.to_string_lossy(), "name": path.file_name().unwrap_or_default().to_string_lossy(), "source": source}),
    )
}
#[tauri::command]
pub async fn open_file(state: tauri::State<'_, Files>) -> Result<Option<Value>, String> {
    let path = rfd::AsyncFileDialog::new()
        .add_filter(
            "Codigo y documentos",
            &["py", "miezee", "txt", "md", "json", "csv", "rtf"],
        )
        .pick_file()
        .await;
    if let Some(file) = path {
        let value = document(file.path())?;
        state
            .0
            .lock()
            .map_err(|e| e.to_string())?
            .push(file.path().canonicalize().map_err(|e| e.to_string())?);
        return Ok(Some(value));
    }
    Ok(None)
}
#[tauri::command]
pub async fn open_folder(state: tauri::State<'_, Files>) -> Result<Option<String>, String> {
    if let Some(folder) = rfd::AsyncFileDialog::new().pick_folder().await {
        allowed(folder.path())?;
        let path = folder.path().canonicalize().map_err(|e| e.to_string())?;
        state
            .0
            .lock()
            .map_err(|e| e.to_string())?
            .push(path.clone());
        return Ok(Some(path.to_string_lossy().into_owned()));
    }
    Ok(None)
}
fn authorized(state: &Files, path: &Path) -> Result<(), String> {
    allowed(path)?;
    let resolved = path.canonicalize().map_err(|e| e.to_string())?;
    let examples = services::project_root()
        .join("examples")
        .canonicalize()
        .map_err(|e| e.to_string())?;
    if resolved.starts_with(examples)
        || state
            .0
            .lock()
            .map_err(|e| e.to_string())?
            .iter()
            .any(|p| resolved == *p || (p.is_dir() && resolved.starts_with(p)))
    {
        return Ok(());
    }
    Err("Selecciona el archivo o la carpeta desde Archivo.".into())
}
#[tauri::command]
pub fn read_file(state: tauri::State<'_, Files>, path: String) -> Result<Value, String> {
    authorized(&state, Path::new(&path))?;
    document(Path::new(&path))
}

fn collect_with<F>(
    root: &Path,
    files: &mut Vec<Value>,
    warnings: &mut Vec<String>,
    read: &mut F,
) -> Result<(), String>
where
    F: FnMut(&Path) -> std::io::Result<std::fs::ReadDir>,
{
    for entry in read(root).map_err(|e| e.to_string())? {
        let entry = match entry {
            Ok(entry) => entry,
            Err(error) => {
                warnings.push(format!("{}: {error}", root.display()));
                continue;
            }
        };
        let path = entry.path();
        let file_type = match entry.file_type() {
            Ok(value) => value,
            Err(error) => {
                warnings.push(format!("{}: {error}", path.display()));
                continue;
            }
        };
        if file_type.is_symlink() {
            continue;
        }
        if path.is_dir() {
            if ![
                ".git",
                ".venv",
                "node_modules",
                "__pycache__",
                "target",
                "dist",
            ]
            .contains(&entry.file_name().to_string_lossy().as_ref())
            {
                if let Err(error) = collect_with(&path, files, warnings, read) {
                    warnings.push(format!("{}: {error}", path.display()));
                }
            }
        } else if ["py", "miezee", "txt", "md", "json", "csv", "rtf"].contains(
            &path
                .extension()
                .unwrap_or_default()
                .to_string_lossy()
                .as_ref(),
        ) && allowed(&path).is_ok()
        {
            files.push(json!({"path": path.to_string_lossy(), "name": path.file_name().unwrap_or_default().to_string_lossy()}));
        }
    }
    Ok(())
}
#[tauri::command]
pub fn list_files(state: tauri::State<'_, Files>, root: Option<String>) -> Result<Value, String> {
    let root = root
        .map(PathBuf::from)
        .unwrap_or_else(|| services::project_root().join("examples"));
    authorized(&state, &root)?;
    let mut files = Vec::new();
    let mut warnings = Vec::new();
    collect_with(&root, &mut files, &mut warnings, &mut |path| {
        std::fs::read_dir(path)
    })?;
    files.sort_by_key(|f| f["path"].as_str().unwrap_or("").to_owned());
    Ok(json!({"root": root.to_string_lossy(), "files": files, "warnings": warnings}))
}
#[tauri::command]
pub async fn save_file(
    state: tauri::State<'_, Files>,
    path: Option<String>,
    source: String,
    name: String,
    open_paths: Vec<String>,
) -> Result<Option<Value>, String> {
    let target = if let Some(path) = path {
        authorized(&state, Path::new(&path))?;
        PathBuf::from(path)
    } else if let Some(file) = rfd::AsyncFileDialog::new()
        .set_file_name(&name)
        .save_file()
        .await
    {
        file.path().to_owned()
    } else {
        return Ok(None);
    };
    allowed(&target)?;
    let replaced_paths = if let Ok(resolved) = target.canonicalize() {
        open_paths
            .iter()
            .filter(|path| Path::new(path).canonicalize().ok().as_ref() == Some(&resolved))
            .cloned()
            .collect::<Vec<_>>()
    } else {
        Vec::new()
    };
    if !replaced_paths.is_empty() && rfd::AsyncMessageDialog::new().set_title("Archivo ya abierto")
            .set_description("El destino ya esta abierto en otra pestana. Reemplazar su contenido y conservar una sola pestana? Los cambios sin guardar de la otra pestana se descartaran.")
            .set_buttons(rfd::MessageButtons::YesNo).show().await != rfd::MessageDialogResult::Yes { return Ok(None); }
    std::fs::write(&target, source).map_err(|e| e.to_string())?;
    state
        .0
        .lock()
        .map_err(|e| e.to_string())?
        .push(target.canonicalize().map_err(|e| e.to_string())?);
    let mut saved = document(&target)?;
    saved["replacedPaths"] = json!(replaced_paths);
    Ok(Some(saved))
}

#[tauri::command]
pub async fn confirm_close() -> bool {
    rfd::AsyncMessageDialog::new()
        .set_title("Miezee IDE")
        .set_description("Descartar los cambios sin guardar?")
        .set_buttons(rfd::MessageButtons::YesNo)
        .show()
        .await
        == rfd::MessageDialogResult::Yes
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn internal_source_is_hidden_but_examples_are_available() {
        assert!(allowed(&services::project_root().join("app.py")).is_err());
        assert!(allowed(&services::project_root().join("examples/correcto_consola.py")).is_ok());
    }
    #[test]
    fn unreadable_subfolder_does_not_hide_accessible_files() {
        struct Temp(PathBuf);
        impl Drop for Temp {
            fn drop(&mut self) {
                assert!(self.0.starts_with(std::env::temp_dir()));
                let _ = std::fs::remove_dir_all(&self.0);
            }
        }
        let root = Temp(std::env::temp_dir().join(format!(
                "miezee-explorer-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            )));
        std::fs::create_dir_all(root.0.join("blocked")).unwrap();
        std::fs::write(root.0.join("visible.py"), "print(1)").unwrap();
        let mut files = Vec::new();
        let mut warnings = Vec::new();
        collect_with(&root.0, &mut files, &mut warnings, &mut |path| {
            if path.ends_with("blocked") {
                Err(std::io::Error::from(std::io::ErrorKind::PermissionDenied))
            } else {
                std::fs::read_dir(path)
            }
        })
        .unwrap();
        assert_eq!(files.len(), 1);
        assert_eq!(files[0]["name"], "visible.py");
        assert_eq!(warnings.len(), 1);
        assert!(warnings[0].contains("blocked"));
    }
}
