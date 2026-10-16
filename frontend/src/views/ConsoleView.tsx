import { useEffect, useRef, useState } from "react";
import { Square, Eraser } from "lucide-react";

export function ConsoleView(props: {
  output: string;
  running: boolean;
  submit: (text: string) => void;
  stop: () => void;
  clear: () => void;
}) {
  const [input, setInput] = useState("");
  const output = useRef<HTMLPreElement>(null);
  const field = useRef<HTMLInputElement>(null);
  useEffect(() => {
    output.current?.scrollTo({ top: output.current.scrollHeight });
  }, [props.output]);
  useEffect(() => {
    if (props.running) field.current?.focus();
  }, [props.running]);
  return (
    <div className="console-view">
      <div className="console-actions">
        <button
          title="Detener ejecucion"
          disabled={!props.running}
          onClick={props.stop}
        >
          <Square size={14} />
        </button>
        <button title="Limpiar consola" onClick={props.clear}>
          <Eraser size={16} />
        </button>
      </div>
      <pre ref={output} className="console-output" aria-live="polite">
        {props.output}
      </pre>
      <form
        className="console-input"
        onSubmit={(event) => {
          event.preventDefault();
          props.submit(input);
          setInput("");
        }}
      >
        <label htmlFor="console-input">&gt;_</label>
        <input
          id="console-input"
          ref={field}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          autoComplete="off"
          aria-label="Entrada de consola"
        />
      </form>
    </div>
  );
}
