import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CircleHelp, Eraser, FileText, Image, Paperclip, Send, Square, Wrench, X } from "lucide-react";
import { isTauri } from "@tauri-apps/api/core";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import type { ChatAttachment, ChatMessage } from "../models/ide";
import { chatCommands } from "../controllers/useChatController";

export function ChatView(props: {
  messages: ChatMessage[];
  busy: boolean;
  send: (text: string, attachments?: ChatAttachment[]) => void;
  attachFiles: (paths?: string[]) => Promise<{ attachments: ChatAttachment[]; errors: string[] }>;
  attachments: ChatAttachment[];
  addAttachments: (attachments: ChatAttachment[]) => void;
  removeAttachment: (id: string) => void;
  clearAttachments: () => void;
  stop: () => void;
  clear: () => void;
  explain: () => void;
}) {
  const [text, setText] = useState("");
  const [selected, setSelected] = useState(0);
  const [attachmentError, setAttachmentError] = useState("");
  const [dragging, setDragging] = useState(false);
  const field = useRef<HTMLTextAreaElement>(null);
  const history = useRef<HTMLDivElement>(null);
  const busy = useRef(props.busy);
  busy.current = props.busy;
  const commands =
    text.startsWith("/") && !text.includes(" ")
      ? chatCommands.filter((c) =>
          c.toLowerCase().startsWith(text.toLowerCase()),
        )
      : [];
  useEffect(() => {
    history.current?.scrollTo({ top: history.current.scrollHeight });
  }, [props.messages, props.busy]);
  useEffect(() => setSelected(0), [text]);
  useEffect(() => {
    if (!isTauri()) return;
    let unlisten: (() => void) | undefined;
    void getCurrentWebview()
      .onDragDropEvent((event) => {
        const payload = event.payload;
        const panel = history.current?.closest(".assistant");
        const bounds = panel?.getBoundingClientRect();
        const scale = window.devicePixelRatio || 1;
        const position = "position" in payload ? payload.position : undefined;
        const isOverChat = Boolean(
          bounds &&
            position &&
            position.x / scale >= bounds.left &&
            position.x / scale <= bounds.right &&
            position.y / scale >= bounds.top &&
            position.y / scale <= bounds.bottom,
        );
        if (event.payload.type === "drop") {
          setDragging(false);
          if (isOverChat) void addAttachments(event.payload.paths);
        } else if (event.payload.type === "leave") {
          setDragging(false);
        } else {
          setDragging(isOverChat);
        }
      })
      .then((dispose) => {
        unlisten = dispose;
      });
    return () => unlisten?.();
  }, []);
  async function addAttachments(paths?: string[]) {
    if (busy.current) return;
    setAttachmentError("");
    try {
      const result = await props.attachFiles(paths);
      if (props.attachments.length + result.attachments.length > 5)
        setAttachmentError("Solo se admiten 5 archivos por consulta.");
      props.addAttachments(result.attachments);
      if (result.errors.length) setAttachmentError(result.errors.join("\n"));
      field.current?.focus();
    } catch (error) {
      setAttachmentError(String(error));
    }
  }
  function insert(command: string) {
    setText(`${command} `);
    field.current?.focus();
  }
  function submit() {
    if (!text.trim() || props.busy) return;
    props.send(text.trim(), props.attachments);
    setText("");
    props.clearAttachments();
    setAttachmentError("");
  }
  return (
    <>
      <div className="chat-history" ref={history}>
        {props.messages.map((message, index) => (
          <article key={index} className={`bubble ${message.role}`}>
            <small>{message.role === "user" ? "Tu" : "Asistente"}</small>
            {message.attachments && message.attachments.length > 0 && (
              <div className="message-attachments">
                {message.attachments.map((name, attachmentIndex) => (
                  <span key={`${name}-${attachmentIndex}`}><FileText size={12} />{name}</span>
                ))}
              </div>
            )}
            <Markdown
              remarkPlugins={[remarkGfm]}
              components={{
                strong: ({ node, children }) =>
                  message.text
                    .slice(node?.position?.start.offset ?? 0)
                    .startsWith("__") ? (
                    <u>{children}</u>
                  ) : (
                    <strong>{children}</strong>
                  ),
                a: ({ children, href }) => (
                  <a href={href} target="_blank" rel="noreferrer">
                    {children}
                  </a>
                ),
              }}
            >
              {message.text}
            </Markdown>
          </article>
        ))}
        {props.busy && (
          <div
            className="chat-pending"
            role="status"
            aria-live="polite"
            aria-label="El asistente esta pensando"
          >
            <span className="pending-label">Pensando</span>
            <span className="pending-dots" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
          </div>
        )}
      </div>
      <div className={`chat-composer ${dragging ? "dragging" : ""}`}>
        {commands.length > 0 && (
          <div className="slash-menu" role="listbox">
            {commands.map((command, index) => (
              <button
                key={command}
                role="option"
                aria-selected={selected === index}
                className={selected === index ? "active" : ""}
                onClick={() => insert(command)}
              >
                {command}
              </button>
            ))}
          </div>
        )}
        <div className="composer-content">
          {props.attachments.length > 0 && (
            <div className="attachment-list" aria-label="Archivos adjuntos">
              {props.attachments.map((attachment) => (
                <span
                  className="attachment-chip"
                  key={attachment.id}
                  title={attachment.truncated ? "El texto fue recortado al limite de contexto" : attachment.name}
                >
                  {attachment.kind === "image" ? <Image size={13} /> : <FileText size={13} />}
                  <span>{attachment.name}</span>
                  <button
                    type="button"
                    title={`Quitar ${attachment.name}`}
                    onClick={() => props.removeAttachment(attachment.id)}
                  ><X size={12} /></button>
                </span>
              ))}
            </div>
          )}
          {attachmentError && <div className="attachment-error" role="alert">{attachmentError}</div>}
          <textarea
            ref={field}
            value={text}
            onChange={(event) => setText(event.target.value)}
            aria-label="Mensaje al asistente"
            placeholder={props.attachments.length ? "Indica que quieres hacer con el contenido cargado..." : "Mensaje..."}
            onKeyDown={(event) => {
            if (
              commands.length &&
              ["ArrowDown", "ArrowUp", "Tab"].includes(event.key)
            ) {
              event.preventDefault();
              if (event.key === "Tab") insert(commands[selected]);
              else
                setSelected(
                  (value) =>
                    (value +
                      (event.key === "ArrowDown" ? 1 : commands.length - 1)) %
                    commands.length,
                );
            } else if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (commands.length) insert(commands[selected]);
              else submit();
            } else if (event.key === "Escape") setText("");
            }}
          />
        </div>
        <button
          type="button"
          className="attach-button"
          title="Adjuntar documentos o imagenes"
          disabled={props.busy || props.attachments.length >= 5}
          onClick={() => void addAttachments()}
        >
          <Paperclip size={17} />
        </button>
        <button
          title="Enviar mensaje"
          disabled={props.busy || !text.trim()}
          onClick={submit}
        >
          <Send size={17} />
        </button>
      </div>
      <footer className="chat-tools">
        <button
          title="Detener respuesta"
          disabled={!props.busy}
          onClick={props.stop}
        >
          <Square size={16} />
        </button>
        <button title="Explicar error seleccionado" onClick={props.explain}>
          <CircleHelp size={18} />
        </button>
        <button
          title="Corregir codigo actual"
          disabled={props.busy}
          onClick={() =>
            props.send(
              "/corregir corrige el archivo actual y explica los cambios",
            )
          }
        >
          <Wrench size={17} />
        </button>
        <button title="Limpiar chat" onClick={props.clear}>
          <Eraser size={18} />
        </button>
      </footer>
    </>
  );
}
