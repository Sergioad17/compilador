import { X } from "lucide-react";
import type { Preferences } from "../models/ide";
export function SettingsView(props: {
  value: Preferences;
  update: (value: Preferences) => void;
  close: () => void;
}) {
  return (
    <div className="modal-backdrop" onClick={props.close}>
      <section
        role="dialog"
        aria-modal="true"
        aria-label="Configuracion"
        className="settings-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <header>
          <h2>Configuracion</h2>
          <button title="Cerrar configuracion" onClick={props.close}>
            <X size={18} />
          </button>
        </header>
        <label>
          Tema
          <select
            value={props.value.theme}
            onChange={(event) =>
              props.update({
                ...props.value,
                theme: event.target.value as Preferences["theme"],
              })
            }
          >
            <option>Default</option>
            <option>Morado</option>
          </select>
        </label>
        <label>
          Tamano de fuente
          <input
            type="number"
            min={10}
            max={28}
            value={props.value.fontSize}
            onChange={(event) =>
              props.update({
                ...props.value,
                fontSize: Math.max(
                  10,
                  Math.min(28, Number(event.target.value)),
                ),
              })
            }
          />
        </label>
        <label>
          URL de Ollama
          <input
            value={props.value.url}
            onChange={(event) =>
              props.update({ ...props.value, url: event.target.value })
            }
          />
        </label>
        <label>
          Modelo local
          <input
            value={props.value.model}
            onChange={(event) =>
              props.update({ ...props.value, model: event.target.value })
            }
          />
        </label>
      </section>
    </div>
  );
}
