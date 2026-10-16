import { useEffect, useRef, useState } from "react";
export interface Action {
  name: string;
  run: () => void;
  shortcut?: string;
}
export function CommandPalette(props: {
  actions: Action[];
  close: () => void;
}) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const field = useRef<HTMLInputElement>(null);
  const filtered = props.actions.filter((action) =>
    action.name.toLowerCase().includes(query.toLowerCase()),
  );
  useEffect(() => {
    field.current?.focus();
  }, []);
  useEffect(() => setSelected(0), [query]);
  function choose(action: Action) {
    props.close();
    action.run();
  }
  return (
    <div className="modal-backdrop palette-backdrop" onClick={props.close}>
      <section
        className="command-palette"
        role="dialog"
        aria-modal="true"
        aria-label="Paleta de comandos"
        onClick={(event) => event.stopPropagation()}
      >
        <input
          ref={field}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label="Buscar comando"
          placeholder=">"
          onKeyDown={(event) => {
            if (event.key === "Escape") props.close();
            if (event.key === "Enter" && filtered[selected])
              choose(filtered[selected]);
            if (event.key === "ArrowDown" && filtered.length) {
              event.preventDefault();
              setSelected((value) => (value + 1) % filtered.length);
            }
            if (event.key === "ArrowUp" && filtered.length) {
              event.preventDefault();
              setSelected(
                (value) => (value + filtered.length - 1) % filtered.length,
              );
            }
          }}
        />
        <div role="listbox">
          {filtered.map((action, index) => (
            <button
              key={action.name}
              role="option"
              aria-selected={index === selected}
              className={index === selected ? "active" : ""}
              onClick={() => choose(action)}
            >
              {action.name}
              <kbd>{action.shortcut}</kbd>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
