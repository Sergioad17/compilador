import { useEffect, useRef, useState } from "react";
import type { Analysis, Document, Panel, Preferences } from "../models/ide";
import { backend } from "../services/backend";
import { isTauri } from "@tauri-apps/api/core";
import { useConsoleController } from "./useConsoleController";
import { useChatController, chatCommands } from "./useChatController";

export function useIdeController() {
  const [documents, setDocuments] = useState<Document[]>([
    { id: "untitled", name: "sin_titulo.py", source: "" },
  ]);
  const [activeId, setActiveId] = useState("untitled");
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [translation, setTranslation] = useState("");
  const [panel, setPanel] = useState<Panel>("Problemas");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [line, setLine] = useState<{ number: number; token: number } | null>(
    null,
  );
  const revision = useRef(0);
  const saving = useRef(false);
  const [root, setRoot] = useState<string>();
  const [hasPreferences] = useState(() =>
    Boolean(localStorage.getItem("miezee.preferences")),
  );
  const [files, setFiles] = useState<{ name: string; path: string }[]>([]);
  const [preferences, setPreferences] = useState<Preferences>(() => {
    try {
      return {
        theme: "Default",
        fontSize: 14,
        url: "http://localhost:11434",
        model: "qwen3:14b",
        ...JSON.parse(localStorage.getItem("miezee.preferences") || "{}"),
      };
    } catch {
      return {
        theme: "Default",
        fontSize: 14,
        url: "http://localhost:11434",
        model: "qwen3:14b",
      };
    }
  });
  const [visibility, setVisibility] = useState({
    explorer: true,
    chat: true,
    bottom: true,
  });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [aiStatus, setAiStatus] = useState("Comprobando modelo local...");
  const [cursor, setCursor] = useState({ line: 1, column: 1 });
  const terminal = useConsoleController(setNotice);
  const active = documents.find((document) => document.id === activeId)!;
  const currentDocuments = useRef(documents);
  currentDocuments.current = documents;
  useEffect(() => {
    void refresh();
  }, []);
  useEffect(() => {
    if (!hasPreferences && isTauri())
      void backend
        .settings()
        .then((settings) =>
          setPreferences((value) => ({ ...value, ...settings })),
        )
        .catch((error) => setNotice(String(error)));
  }, []);
  useEffect(() => {
    localStorage.setItem("miezee.preferences", JSON.stringify(preferences));
  }, [preferences]);
  useEffect(() => {
    if (!isTauri()) {
      setAiStatus("Vista web · backend desconectado");
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      backend
        .status(preferences.url, preferences.model)
        .then((result) => {
          if (!cancelled) setAiStatus(result.text);
        })
        .catch(() => {
          if (!cancelled) setAiStatus("Local no disponible");
        });
    }, 500);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [preferences.url, preferences.model]);
  async function refresh(folder = root) {
    try {
      const data = await backend.listFiles(folder);
      setRoot(data.root);
      setFiles(data.files);
      setNotice(data.warnings?.length ? "Algunas carpetas no pudieron leerse:\n" + data.warnings.join("\n") : "");
    } catch (error) {
      setNotice(String(error));
    }
  }
  function invalidate() {
    revision.current++;
    setAnalysis(null);
    setTranslation("");
    setLine(null);
  }
  function select(id: string) {
    invalidate();
    setActiveId(id);
  }
  function update(source: string) {
    invalidate();
    setDocuments((items) =>
      items.map((item) => (item.id === activeId ? { ...item, source } : item)),
    );
  }
  function open(document: Document) {
    const existing = documents.find(
      (item) =>
        item.id === document.id ||
        (document.path && item.path === document.path),
    );
    if (existing) {
      select(existing.id);
      return;
    }
    setDocuments((items) =>
      items.some((item) => item.id === document.id)
        ? items
        : [...items, { ...document, savedSource: document.source }],
    );
    select(document.id);
  }
  function create() {
    open({ id: crypto.randomUUID(), name: "sin_titulo.py", source: "" });
  }
  async function close(id: string) {
    const document = documents.find((item) => item.id === id)!;
    if (
      document.source !== (document.savedSource ?? "") &&
      !(await backend.confirmClose())
    )
      return;
    if (documents.length === 1) {
      const id = crypto.randomUUID();
      setDocuments([{ id, name: "sin_titulo.py", source: "" }]);
      select(id);
      return;
    }
    setDocuments((items) => items.filter((item) => item.id !== id));
    if (activeId === id) select(documents.find((item) => item.id !== id)!.id);
  }
  async function fileAction(
    action: "open" | "folder" | "save" | "saveAs",
    path?: string,
  ) {
    if ((action === "save" || action === "saveAs") && saving.current) return;
    try {
      if (action === "open") {
        const document = path
          ? await backend.readFile(path)
          : await backend.openFile();
        if (document) open(document);
      } else if (action === "folder") {
        const folder = await backend.openFolder();
        if (folder) await refresh(folder);
      } else {
        saving.current = true;
        const snapshot = active;
        const openPaths = currentDocuments.current.filter(item => item.id !== snapshot.id && item.path).map(item => item.path!);
        const saved = await backend.save(snapshot, action === "saveAs", openPaths);
        if (saved) {
          const normalize = (path?: string) => navigator.platform.startsWith("Win") ? path?.replace(/\\/g, "/").replace(/^\/\/\?\//, "").toLowerCase() : path;
          const samePath = (path?: string) => path !== undefined && (saved.replacedPaths?.includes(path) || normalize(path) === normalize(saved.path));
          const removed = currentDocuments.current.filter(item => item.id !== snapshot.id && samePath(item.path)).map(item => item.id);
          setDocuments((items) =>
            items.filter(item => !removed.includes(item.id)).map((item) =>
              item.id === snapshot.id
                ? {
                    ...item,
                    name: saved.name,
                    path: saved.path,
                    savedSource: snapshot.source,
                  }
                : item,
            ),
          );
          setActiveId(id => removed.includes(id) ? snapshot.id : id);
          await refresh();
        }
      }
    } catch (error) {
      setNotice(String(error));
    } finally {
      if (action === "save" || action === "saveAs") saving.current = false;
    }
  }
  async function run(preview = false) {
    const version = revision.current;
    setVisibility((value) => ({ ...value, bottom: true }));
    setPanel(preview ? "Vista previa" : "Consola");
    const cwd = active.path ? active.path.replace(/[\\/][^\\/]+$/, "") : root;
    const result = await terminal.start(active.source, cwd);
    if (result && version === revision.current) {
      setAnalysis(result);
      if (!result.ok) setPanel("Problemas");
    }
  }
  async function applyGenerated(code: string, id: string, original: string) {
    const document = currentDocuments.current.find((item) => item.id === id);
    if (
      document &&
      document.source !== original &&
      !(await backend.confirmClose())
    )
      return false;
    invalidate();
    setDocuments((items) => {
      if (!items.some((item) => item.id === id))
        return [...items, { id, name: "generado.py", source: code }];
      return items.map((item) =>
        item.id === id ? { ...item, source: code } : item,
      );
    });
    setActiveId(id);
    return true;
  }
  async function localChat(command: string): Promise<string | null> {
    const lower = command.toLowerCase();
    if (lower === "/ayuda") return chatCommands.join("\n");
    if (lower === "/analizar") {
      await perform("analyze");
      return "Analisis solicitado. Revisa el panel Problemas.";
    }
    if (lower === "/tabla") {
      setPanel("Tabla de simbolos");
      return analysis
        ? analysis.symbols.map((s) => `${s.name}: ${s.type}`).join("\n") ||
            "Tabla vacia."
        : "Analiza el archivo primero.";
    }
    if (lower === "/errores")
      return analysis
        ? analysis.errors
            .map((e) => `${e.code}, linea ${e.line}: ${e.explanation}`)
            .join("\n") || "Sin errores."
        : "Analiza el archivo primero.";
    if (lower === "/estado")
      return `Analizador local disponible. IA: ${aiStatus}. Modelo configurado: ${preferences.model}.`;
    if (lower === "/tipos")
      return "Python: int, float, bool, str, list, tuple, dict, set y clases. Las anotaciones son opcionales.";
    if (lower === "/reglas")
      return "PY01: sintaxis. PY02: funciones. PY03: clases. PY04: asignaciones. Las importaciones y llamadas tambien se validan con las reglas del analizador Python.";
    if (
      lower.startsWith("/") &&
      !chatCommands.some((c) => lower.split(" ")[0] === c.toLowerCase())
    )
      return "Comando no reconocido. Usa /ayuda.";
    return null;
  }
  const chat = useChatController({
    source: active.source,
    documentId: active.id,
    preferences,
    apply: applyGenerated,
    local: localChat,
  });
  function clear() {
    invalidate();
    setNotice("");
    terminal.clear();
  }
  function toggle(name: keyof typeof visibility) {
    setVisibility((value) => ({ ...value, [name]: !value[name] }));
  }
  useEffect(() => {
    function keyboard(event: KeyboardEvent) {
      const ctrl = event.ctrlKey || event.metaKey;
      const key = event.key.toLowerCase();
      if (key === "escape") {
        setSettingsOpen(false);
        setPaletteOpen(false);
        document
          .querySelectorAll(".menubar details[open]")
          .forEach((menu) => menu.removeAttribute("open"));
      }
      let action: (() => void) | undefined;
      if (ctrl && key === "s")
        action = () => {
          void fileAction(event.shiftKey ? "saveAs" : "save");
        };
      else if (ctrl && key === "o")
        action = () => {
          void fileAction("open");
        };
      else if (ctrl && key === "k")
        action = () => {
          void fileAction("folder");
        };
      else if (ctrl && key === "n") action = create;
      else if (ctrl && key === "b") action = () => toggle("explorer");
      else if (ctrl && key === "j") action = () => toggle("bottom");
      else if (ctrl && event.shiftKey && key === "c")
        action = () => toggle("chat");
      else if (ctrl && event.shiftKey && key === "p")
        action = () => setPaletteOpen(true);
      else if (ctrl && key === "l") action = clear;
      else if (key === "f5")
        action = () => {
          void perform("analyze");
        };
      else if (key === "f6")
        action = () => {
          void run();
        };
      else if (key === "f7")
        action = () => {
          void run(true);
        };
      else if (key === "f8")
        action = () => {
          setPanel("Consola");
          setVisibility((v) => ({ ...v, bottom: true }));
        };
      else if (key === "f9")
        action = () => {
          void perform("translate");
        };
      if (action) {
        event.preventDefault();
        action();
      }
    }
    window.addEventListener("keydown", keyboard, true);
    return () => window.removeEventListener("keydown", keyboard, true);
  });
  async function perform(operation: "analyze" | "translate") {
    if (busy) return;
    const version = revision.current;
    setBusy(true);
    setNotice("");
    setVisibility((value) => ({ ...value, bottom: true }));
    try {
      if (operation === "analyze") {
        const result = await backend.analyze(active.source);
        if (version === revision.current) {
          setAnalysis(result);
          setPanel("Problemas");
        }
      } else {
        const result = await backend.translate(active.source);
        if (version === revision.current) {
          setTranslation(result.translation);
          setPanel("Traduccion");
        }
      }
    } catch (error) {
      setNotice(String(error));
    } finally {
      setBusy(false);
    }
  }
  return {
    documents,
    active,
    analysis,
    translation,
    panel,
    busy,
    notice,
    line,
    files,
    root,
    refresh,
    fileAction,
    run,
    terminal,
    chat,
    clear,
    preferences,
    setPreferences,
    aiStatus,
    cursor,
    setCursor,
    visibility,
    toggle,
    settingsOpen,
    setSettingsOpen,
    paletteOpen,
    setPaletteOpen,
    select,
    update,
    open,
    create,
    close,
    setPanel,
    perform,
    goToLine: (number: number) => setLine({ number, token: Date.now() }),
  };
}
