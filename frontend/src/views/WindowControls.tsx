import { Minus, Square, Copy, X } from "lucide-react";
import { useWindowController } from "../controllers/useWindowController";

export function WindowControls() {
  const window = useWindowController();
  if (!window.native) return null;
  return <div className="window-controls">
    <button title="Minimizar" aria-label="Minimizar" onClick={window.minimize}><Minus size={16} /></button>
    <button title={window.maximized ? "Restaurar ventana" : "Maximizar"} aria-label={window.maximized ? "Restaurar ventana" : "Maximizar"} onClick={window.maximize}>
      {window.maximized ? <Copy size={14} /> : <Square size={14} />}
    </button>
    <button className="window-close" title="Cerrar ventana" aria-label="Cerrar ventana" onClick={window.close}><X size={17} /></button>
  </div>;
}
