use serde_json::{json, Value};
use std::{
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
};

pub fn project_root() -> PathBuf {
    std::env::var_os("MIEZEE_PROJECT_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."))
}

pub fn python_command() -> Command {
    let executable = std::env::var_os("MIEZEE_PYTHON").unwrap_or_else(|| "python".into());
    let mut command = Command::new(executable);
    command
        .env("PYTHONIOENCODING", "utf-8")
        .env("PYTHONUTF8", "1");
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    command
}

pub fn python(operation: &str, source: &str) -> Result<Value, String> {
    let executable = std::env::var_os("MIEZEE_PYTHON").unwrap_or_else(|| "python".into());
    let mut command = Command::new(executable);
    command
        .current_dir(project_root())
        .args(["-X", "utf8", "-m", "miezee.backend.cli", operation])
        .env("PYTHONIOENCODING", "utf-8")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = command
        .spawn()
        .map_err(|error| format!("No se pudo iniciar Python: {error}"))?;
    let write_result = child
        .stdin
        .take()
        .ok_or("Entrada Python no disponible")?
        .write_all(source.as_bytes());
    if let Err(error) = write_result {
        let _ = child.kill();
        let _ = child.wait();
        return Err(error.to_string());
    }
    let output = child
        .wait_with_output()
        .map_err(|error| error.to_string())?;
    if !output.status.success() {
        return Err(String::from_utf8_lossy(&output.stderr).into_owned());
    }
    serde_json::from_slice(&output.stdout)
        .map_err(|error| format!("Respuesta Python invalida: {error}"))
}

pub fn examples() -> Result<Value, String> {
    let root = project_root().join("examples");
    let mut files = Vec::new();
    for entry in std::fs::read_dir(&root).map_err(|error| error.to_string())? {
        let path = entry.map_err(|error| error.to_string())?.path();
        if path.is_file() && path.extension().and_then(|value| value.to_str()) == Some("py") {
            let name = path
                .file_name()
                .ok_or("Nombre de archivo invalido")?
                .to_string_lossy()
                .into_owned();
            let source = std::fs::read_to_string(&path).map_err(|error| error.to_string())?;
            files.push(json!({"id": format!("example:{name}"), "name": name, "source": source}));
        }
    }
    files.sort_by_key(|file| file["name"].as_str().unwrap_or("").to_owned());
    Ok(Value::Array(files))
}
