import Editor, { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import { useEffect, useRef } from "react";
import type { Analysis } from "../models/ide";

self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
loader.config({ monaco });

export function CodeEditor(props: {
  id: string;
  source: string;
  errors: Analysis["errors"];
  onChange: (source: string) => void;
  line: { number: number; token: number } | null;
  fontSize: number;
  onCursorChange: (cursor: { line: number; column: number }) => void;
}) {
  const editor = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const cursorSubscription = useRef<monaco.IDisposable | null>(null);
  useEffect(() => () => cursorSubscription.current?.dispose(), []);
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
  return (
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
      }}
    />
  );
}
