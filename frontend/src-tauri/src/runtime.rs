use crate::services;
use serde::Serialize;
use serde_json::{json, Value};
use std::{
    io::{Read, Write},
    process::{Child, ChildStdin, Stdio},
    sync::{Arc, Mutex},
    thread,
};

#[derive(Serialize)]
struct Frame {
    stream: &'static str,
    bytes: Vec<u8>,
}
#[derive(Default)]
struct Buffer {
    frames: Vec<Frame>,
    size: usize,
}

#[derive(Default)]
pub struct Runtime(pub Mutex<Option<Session>>);
pub struct Session {
    child: Child,
    input: Option<ChildStdin>,
    output: Arc<Mutex<Buffer>>,
    readers: Vec<thread::JoinHandle<()>>,
}
impl Drop for Session {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

#[tauri::command]
pub async fn start_program(
    state: tauri::State<'_, Runtime>,
    source: String,
    cwd: Option<String>,
) -> Result<Value, String> {
    let input_source = source.clone();
    let analysis =
        tauri::async_runtime::spawn_blocking(move || services::python("analyze", &input_source))
            .await
            .map_err(|e| e.to_string())??;
    if analysis["ok"] != true {
        return Ok(json!({"started": false, "analysis": analysis}));
    }
    let prepared =
        tauri::async_runtime::spawn_blocking(move || services::python("prepare", &source))
            .await
            .map_err(|e| e.to_string())??;
    let mut slot = state.0.lock().map_err(|e| e.to_string())?;
    *slot = None;
    *slot = Some(launch(
        prepared["source"].as_str().ok_or("Codigo invalido")?,
        cwd.map(std::path::PathBuf::from)
            .unwrap_or_else(|| services::project_root().join("examples")),
    )?);
    Ok(json!({"started": true, "analysis": analysis}))
}

fn launch(source: &str, cwd: std::path::PathBuf) -> Result<Session, String> {
    let mut command = services::python_command();
    command
        .args(["-u", "-c", source])
        .current_dir(cwd)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = command.spawn().map_err(|e| e.to_string())?;
    let input = child.stdin.take();
    let output = Arc::new(Mutex::new(Buffer::default()));
    let streams: Vec<Box<dyn Read + Send>> = vec![
        Box::new(child.stdout.take().ok_or("stdout no disponible")?),
        Box::new(child.stderr.take().ok_or("stderr no disponible")?),
    ];
    let readers = streams
        .into_iter()
        .enumerate()
        .map(|(index, mut stream)| {
            let output = output.clone();
            thread::spawn(move || {
                let mut buffer = [0; 4096];
                loop {
                    match stream.read(&mut buffer) {
                        Ok(0) | Err(_) => break,
                        Ok(size) => {
                            if let Ok(mut output) = output.lock() {
                                if output.size < 1024 * 1024 {
                                    output.size += size;
                                    output.frames.push(Frame {
                                        stream: if index == 0 { "stdout" } else { "stderr" },
                                        bytes: buffer[..size].to_vec(),
                                    });
                                }
                            }
                        }
                    }
                }
            })
        })
        .collect();
    Ok(Session {
        child,
        input,
        output,
        readers,
    })
}

#[tauri::command]
pub fn poll_program(state: tauri::State<'_, Runtime>) -> Result<Value, String> {
    let mut slot = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(session) = slot.as_mut() {
        let status = session.child.try_wait().map_err(|e| e.to_string())?;
        if status.is_some() {
            for reader in session.readers.drain(..) {
                let _ = reader.join();
            }
        }
        let output = std::mem::take(&mut *session.output.lock().map_err(|e| e.to_string())?);
        let result = json!({"chunks": output.frames, "running": status.is_none(), "exitCode": status.map(|s| s.code().unwrap_or(-1))});
        if status.is_some() {
            *slot = None;
        }
        return Ok(result);
    }
    Ok(json!({"chunks": [], "running": false, "exitCode": null}))
}

#[tauri::command]
pub fn program_input(state: tauri::State<'_, Runtime>, text: String) -> Result<(), String> {
    let mut slot = state.0.lock().map_err(|e| e.to_string())?;
    let input = slot
        .as_mut()
        .and_then(|s| s.input.as_mut())
        .ok_or("No hay proceso en ejecucion")?;
    writeln!(input, "{text}")
        .and_then(|_| input.flush())
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn stop_program(state: tauri::State<'_, Runtime>) -> Result<(), String> {
    *state.0.lock().map_err(|e| e.to_string())? = None;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn interactive_input_and_unicode_output() {
        let mut session = launch("a = input('Primer numero: ')\nb = input('Segundo numero: ')\nprint('Resultado: ', int(a)+int(b))\nprint('Numero: \\u00f1')", services::project_root()).unwrap();
        let input = session.input.as_mut().unwrap();
        writeln!(input, "1\n2").unwrap();
        input.flush().unwrap();
        assert!(session.child.wait().unwrap().success());
        for reader in session.readers.drain(..) {
            reader.join().unwrap();
        }
        let bytes: Vec<u8> = session
            .output
            .lock()
            .unwrap()
            .frames
            .iter()
            .flat_map(|f| f.bytes.clone())
            .collect();
        let text = String::from_utf8(bytes).unwrap();
        assert!(text.contains("Resultado:  3"));
        assert!(text.contains("Numero: \u{f1}"));
    }
    #[test]
    fn loop_can_be_stopped() {
        let mut session = launch("while True: pass", services::project_root()).unwrap();
        session.child.kill().unwrap();
        assert!(!session.child.wait().unwrap().success());
    }
}
