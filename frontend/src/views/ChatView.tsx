import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send, Square, Eraser, CircleHelp, Wrench } from "lucide-react";
import type { ChatMessage } from "../models/ide";
import { chatCommands } from "../controllers/useChatController";

export function ChatView(props: {
  messages: ChatMessage[];
  busy: boolean;
  send: (text: string) => void;
  stop: () => void;
  clear: () => void;
  explain: () => void;
}) {
  const [text, setText] = useState("");
  const [selected, setSelected] = useState(0);
  const field = useRef<HTMLTextAreaElement>(null);
  const history = useRef<HTMLDivElement>(null);
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
  function insert(command: string) {
    setText(`${command} `);
    field.current?.focus();
  }
  function submit() {
    if (!text.trim() || props.busy) return;
    props.send(text.trim());
    setText("");
  }
  return (
    <>
      <div className="chat-history" ref={history}>
        {props.messages.map((message, index) => (
          <article key={index} className={`bubble ${message.role}`}>
            <small>{message.role === "user" ? "Tu" : "Asistente"}</small>
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
          <div className="chat-pending" role="status">
            Pensando...
          </div>
        )}
      </div>
      <div className="chat-composer">
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
        <textarea
          ref={field}
          value={text}
          onChange={(event) => setText(event.target.value)}
          aria-label="Mensaje al asistente"
          placeholder="Mensaje..."
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
