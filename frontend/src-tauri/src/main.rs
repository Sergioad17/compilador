mod controllers;
mod files;
mod jobs;
mod runtime;
mod services;

fn main() {
    tauri::Builder::default()
        .manage(runtime::Runtime::default())
        .manage(files::Files::default())
        .manage(jobs::Jobs::default())
        .invoke_handler(tauri::generate_handler![
            controllers::python_request,
            controllers::list_examples,
            runtime::start_program,
            runtime::poll_program,
            runtime::program_input,
            runtime::stop_program,
            files::open_file,
            files::attach_chat_files,
            files::open_folder,
            files::read_file,
            files::save_file,
            files::list_files,
            files::confirm_close,
            jobs::cancel_chat
        ])
        .run(tauri::generate_context!())
        .expect("error while running Miezee Tauri app");
}
