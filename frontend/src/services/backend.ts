import { invoke, isTauri } from "@tauri-apps/api/core";
import type { Analysis, ChatAttachment, Document, IntermediateCode } from "../models/ide";

export async function request<T>(
  command: string,
  args?: Record<string, unknown>,
): Promise<T> {
  if (!isTauri())
    throw new Error(
      "Abre Miezee con npm run tauri dev para conectar el backend Python.",
    );
  return invoke<T>(command, args);
}
export const backend = {
  analyze: (source: string) =>
    request<Analysis>("python_request", { operation: "analyze", source }),
  translate: (source: string) =>
    request<{ translation: string }>("python_request", {
      operation: "translate",
      source,
    }),
  intermediate: (source: string) =>
    request<IntermediateCode>("python_request", {
      operation: "intermediate",
      source,
    }),
  examples: () => request<Document[]>("list_examples"),
  openFile: () => request<Document | null>("open_file"),
  openFolder: () => request<string | null>("open_folder"),
  readFile: (path: string) => request<Document>("read_file", { path }),
  listFiles: (root?: string) =>
    request<{ root: string; files: { name: string; path: string }[]; warnings?: string[] }>(
      "list_files",
      { root: root ?? null },
    ),
  save: (document: Document, saveAs: boolean, openPaths: string[]) =>
    request<Document | null>("save_file", {
      path: saveAs ? null : (document.path ?? null),
      source: document.source,
      name: document.name,
      openPaths,
    }),
  confirmClose: () => request<boolean>("confirm_close"),
  start: (source: string, cwd?: string) =>
    request<{ started: boolean; analysis: Analysis }>("start_program", {
      source,
      cwd: cwd ?? null,
    }),
  poll: () =>
    request<{
      chunks: { stream: "stdout" | "stderr"; bytes: number[] }[];
      running: boolean;
      exitCode: number | null;
    }>("poll_program"),
  input: (text: string) => request<void>("program_input", { text }),
  stop: () => request<void>("stop_program"),
  chat: (payload: object, requestId: string) =>
    request<{ text: string; code: string | null }>("python_request", {
      operation: "chat",
      source: JSON.stringify(payload),
      requestId,
    }),
  cancelChat: (requestId: string) =>
    request<void>("cancel_chat", { requestId }),
  attachChatFiles: (paths?: string[]) =>
    request<{ attachments: ChatAttachment[]; errors: string[] }>(
      "attach_chat_files",
      { paths: paths ?? null },
    ),
  status: (url: string, model: string) =>
    request<{ available: boolean; text: string }>("python_request", {
      operation: "status",
      source: JSON.stringify({ url, model }),
    }),
  settings: () =>
    request<{ url: string; model: string }>("python_request", {
      operation: "settings",
      source: "",
    }),
};
