import Editor, { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import { useEffect, useRef, useState } from "react";
import { Clipboard, Command, Copy, MessageCircleQuestion, Redo2, Scissors, Undo2 } from "lucide-react";
import type { Analysis, ChatAttachment } from "../models/ide";

self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
loader.config({ monaco });

export function CodeEditor(props: {
  id: string;
  name: string;
  source: string;
  errors: Analysis["errors"];
  onChange: (source: string) => void;
  line: { number: number; token: number } | null;
  fontSize: number;
  onCursorChange: (cursor: { line: number; column: number }) => void;
  attachToChat: (attachment: ChatAttachment) => void;
  openCommandPalette: () => void;
}) {
  const editor = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const cursorSubscription = useRef<monaco.IDisposable | null>(null);
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    selection: string;
    startLine: number;
    endLine: number;
  } | null>(null);
  useEffect(() => () => cursorSubscription.current?.dispose(), []);
  useEffect(() => {
    if (!contextMenu) return;
    const close = () => setContextMenu(null);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("pointerdown", close);
    window.addEventListener("blur", close);
    window.addEventListener("resize", close);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", close);
      window.removeEventListener("blur", close);
      window.removeEventListener("resize", close);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [contextMenu]);
  useEffect(() => {
    const instance = editor.current;
    const position = instance?.getPosition();
    if (position) props.onCursorChange({ line: position.lineNumber, column: position.column });
  }, [props.id, props.onCursorChange]);
  useEffect(() => {
    const model = editor.current?.getModel();
    if (model)
      monaco.editor.setModelMarkers(
        model,
        "miezee",
        props.errors.map((error) => {
          const line = Math.max(1, Math.min(error.line, model.getLineCount()));
          return {
            severity: monaco.MarkerSeverity.Error,
            message: `${error.code}: ${error.explanation}`,
            startLineNumber: line,
            endLineNumber: line,
            startColumn: 1,
            endColumn: model.getLineMaxColumn(line),
          };
        }),
      );
  }, [props.errors, props.id, props.source]);
  useEffect(() => {
    if (props.line) {
      editor.current?.revealLineInCenter(props.line.number);
      editor.current?.setPosition({ lineNumber: props.line.number, column: 1 });
      editor.current?.focus();
    }
  }, [props.line]);

  function openContextMenu(event: React.MouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    const selection = editor.current?.getSelection();
    const model = editor.current?.getModel();
    const selectedText = selection && model ? model.getValueInRange(selection) : "";
    const width = 254;
    const height = 292;
    setContextMenu({
      x: Math.max(8, Math.min(event.clientX, window.innerWidth - width - 8)),
      y: Math.max(8, Math.min(event.clientY, window.innerHeight - height - 8)),
      selection: selectedText,
      startLine: selection?.startLineNumber ?? 1,
      endLine: selection?.endLineNumber ?? 1,
    });
  }

  function runEditorAction(action: string) {
    editor.current?.trigger("context-menu", action, null);
    editor.current?.focus();
    setContextMenu(null);
  }

  function explainSelection() {
    if (!contextMenu?.selection.trim()) return;
    const lines = contextMenu.startLine === contextMenu.endLine
      ? `linea ${contextMenu.startLine}`
      : `lineas ${contextMenu.startLine}-${contextMenu.endLine}`;
    props.attachToChat({
      id: `editor-selection-${crypto.randomUUID()}`,
      name: `${props.name} (${lines})`,
      kind: "text",
      mediaType: "text/x-python",
      content: contextMenu.selection,
      size: new TextEncoder().encode(contextMenu.selection).byteLength,
      truncated: false,
      selectionContext: {
        sourceName: props.name,
        language: "python",
        startLine: contextMenu.startLine,
        endLine: contextMenu.endLine,
        fullSource: props.source,
      },
    });
    setContextMenu(null);
  }

  return (
    <div className="code-editor" onContextMenu={openContextMenu}>
      <Editor
        path={props.id}
        language="python"
        theme="vs-dark"
        value={props.source}
        onChange={(value) => props.onChange(value ?? "")}
        onMount={(instance) => {
          editor.current = instance;
          cursorSubscription.current = instance.onDidChangeCursorPosition(event => props.onCursorChange({ line: event.position.lineNumber, column: event.position.column }));
        }}
        options={{
          automaticLayout: true,
          fontSize: props.fontSize,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          padding: { top: 16 },
          tabSize: 4,
          contextmenu: false,
        }}
      />
      {contextMenu && (
        <div
          className="editor-context-menu"
          role="menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onPointerDown={(event) => event.stopPropagation()}
        >
          <button type="button" role="menuitem" onClick={() => runEditorAction("undo")}>
            <Undo2 size={15} /><span>Deshacer</span><kbd>Ctrl+Z</kbd>
          </button>
          <button type="button" role="menuitem" onClick={() => runEditorAction("redo")}>
            <Redo2 size={15} /><span>Rehacer</span><kbd>Ctrl+Y</kbd>
          </button>
          <div className="context-menu-separator" role="separator" />
          <button type="button" role="menuitem" disabled={!contextMenu.selection} onClick={() => runEditorAction("editor.action.clipboardCutAction")}>
            <Scissors size={15} /><span>Cortar</span><kbd>Ctrl+X</kbd>
          </button>
          <button type="button" role="menuitem" disabled={!contextMenu.selection} onClick={() => runEditorAction("editor.action.clipboardCopyAction")}>
            <Copy size={15} /><span>Copiar</span><kbd>Ctrl+C</kbd>
          </button>
          <button type="button" role="menuitem" onClick={() => runEditorAction("editor.action.clipboardPasteAction")}>
            <Clipboard size={15} /><span>Pegar</span><kbd>Ctrl+V</kbd>
          </button>
          <div className="context-menu-separator" role="separator" />
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setContextMenu(null);
              props.openCommandPalette();
            }}
          >
            <Command size={15} /><span>Paleta de comandos</span><kbd>F1</kbd>
          </button>
          <div className="context-menu-separator" role="separator" />
          <button
            type="button"
            role="menuitem"
            disabled={!contextMenu.selection.trim()}
            title={contextMenu.selection.trim() ? "Cargar la seleccion en el chat" : "Selecciona codigo para cargarlo"}
            onClick={explainSelection}
          >
            <MessageCircleQuestion size={15} /><span>¿Que hace, para que sirve?</span>
          </button>
        </div>
      )}
    </div>
  );
}
