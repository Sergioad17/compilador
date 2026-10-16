import { useRef, useState } from "react";
import type { ChatMessage, Preferences } from "../models/ide";
import { backend } from "../services/backend";

export const chatCommands = [
  "/ayuda",
  "/tipos",
  "/reglas",
  "/analizar",
  "/errores",
  "/tabla",
  "/explicar",
  "/corregir",
  "/GenerarPantalla",
  "/GenerarFuncion",
  "/ArreglarPantalla",
  "/limpiar",
  "/estado",
];
export function useChatController(options: {
  source: string;
  documentId: string;
  preferences: Preferences;
  apply: (code: string, id: string, original: string) => Promise<boolean>;
  local: (command: string) => Promise<string | null>;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "Bienvenido a Miezee IDE. Puedes pedirme que cree programas en Miezee, interfaces, menús, archivos o bases de datos. El asistente está preparado para trabajar con tu modelo local de Ollama.",
    },
  ]);
  const [busy, setBusy] = useState(false);
  const requestId = useRef(0);
  const nativeId = useRef<string>();
  const add = (role: ChatMessage["role"], text: string) =>
    setMessages((items) => [...items, { role, text }]);
  async function send(message: string) {
    if (busy || !message.trim()) return;
    if (message.toLowerCase() === "/limpiar") {
      setMessages([]);
      return;
    }
    add("user", message);
    const token = ++requestId.current;
    setBusy(true);
    try {
      const local = await options.local(message);
      if (token !== requestId.current) return;
      if (local !== null) {
        add("assistant", local);
        return;
      }
      const lower = message
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");
      const mode =
        /^\/explicar\b|^\s*(explica|que hace|como funciona|que es)\b/.test(
          lower,
        )
          ? "chat"
          : /\/generarpantalla/.test(lower)
            ? "pantalla"
            : /\/generarfuncion/.test(lower)
              ? "funcion"
              : /\/arreglarpantalla|\/corregir|\b(arregla|corrige|modifica|repara)\b/.test(
                    lower,
                  )
                ? "corregir"
                : /\b(crea|crear|genera|generar|haz|has|realiza|implementa|desarrolla|hagas)\b/.test(
                      lower,
                    ) ||
                    (/\b(quiero|necesito)\b/.test(lower) &&
                      /programa|pantalla|interfaz|codigo|funcion|menu/.test(
                        lower,
                      ))
                  ? /pantalla|interfaz|ventana|menu/.test(lower)
                    ? "pantalla"
                    : "programa"
                  : "chat";
      nativeId.current = crypto.randomUUID();
      const result = await backend.chat(
        {
          message,
          source: options.source,
          mode,
          settings: {
            url: options.preferences.url,
            model: options.preferences.model,
          },
        },
        nativeId.current,
      );
      if (token !== requestId.current) return;
      if (
        result.code &&
        !(await options.apply(result.code, options.documentId, options.source))
      ) {
        add(
          "assistant",
          "Se conservaron tus cambios del editor. La respuesta no se aplico.",
        );
        return;
      }
      add("assistant", result.text);
    } catch (error) {
      if (token === requestId.current) add("assistant", String(error));
    } finally {
      if (token === requestId.current) setBusy(false);
    }
  }
  return {
    messages,
    busy,
    send,
    clear: () => setMessages([]),
    stop: () => {
      requestId.current++;
      if (nativeId.current)
        void backend
          .cancelChat(nativeId.current)
          .catch((error) => add("assistant", String(error)));
      setBusy(false);
    },
  };
}
