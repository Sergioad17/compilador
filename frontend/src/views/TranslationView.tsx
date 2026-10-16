import Editor from "@monaco-editor/react";
import { useEffect, useRef, useState } from "react";
import { FileCode2, LockKeyhole, MessageCircleQuestion, RefreshCw } from "lucide-react";
import * as monaco from "monaco-editor";
import type { ChatAttachment } from "../models/ide";

const LANGUAGE_ID = "miezee-educativo";

if (!monaco.languages.getLanguages().some(({ id }) => id === LANGUAGE_ID)) {
  monaco.languages.register({ id: LANGUAGE_ID });
  monaco.languages.setMonarchTokensProvider(LANGUAGE_ID, {
    keywords: [
      "SI", "SINO", "ENTONCES", "FIN", "MIENTRAS", "PARA", "CADA",
      "EN", "HACER", "SEGUN", "CASO", "INTENTAR", "CAPTURAR",
      "FINALMENTE", "RETORNAR", "ROMPER", "CONTINUAR", "ESPERAR",
      "FUNCION", "PROCEDIMIENTO", "CLASE", "HEREDA", "ASINCRONA", "ANONIMA",
      "AL", "CREAR", "CREACION", "DENTRO", "DONDE",
    ],
    instructions: [
      "DEFINIR", "GUARDAR", "ASIGNAR", "CAMBIAR", "PEDIR", "MOSTRAR", "IMPORTAR",
      "DESDE", "LLAMAR", "CREAR", "CONFIGURAR", "UBICAR", "AGREGAR",
      "CONECTAR", "INICIAR", "LEER", "ESCRIBIR", "ABRIR", "CERRAR",
      "EJECUTAR", "CONFIRMAR", "DESHACER", "CONVERTIR", "ELIMINAR",
      "VERIFICAR", "LANZAR", "USAR", "PRODUCIR", "EVALUAR", "ESTABLECER",
      "COLOCAR", "LIMPIAR", "CONSULTAR", "ACTUALIZAR", "VALIDAR",
      "PROGRAMAR", "PREPARAR",
    ],
    types: [
      "ENTERO", "DECIMAL", "TEXTO", "BOOLEANO", "LISTA", "TUPLA",
      "CONJUNTO", "DICCIONARIO", "INFERIDO", "VENTANA", "ETIQUETA",
      "BOTON", "ENTRADA", "CONTENEDOR", "LIENZO", "TABLA", "MENU",
      "APLICACION", "BASE_DATOS", "CURSOR",
    ],
    constants: ["VERDADERO", "FALSO", "NULO", "NINGUNA"],
    tokenizer: {
      root: [
        [/#.*$/, "comment"],
        [/"([^"\\]|\\.)*"/, "string"],
        [/'([^'\\]|\\.)*'/, "string"],
        [/\b\d+(?:\.\d+)?\b/, "number"],
        [/[A-Z_][A-Z0-9_]*/, {
          cases: {
            "@keywords": "keyword",
            "@instructions": "keyword.control",
            "@types": "type.identifier",
            "@constants": "constant.language",
            "@default": "identifier",
          },
        }],
        [/[+\-*\/%^=<>!]+/, "operator"],
      ],
    },
  });
}

export function TranslationView(props: {
  translation: string;
  sourceName: string;
  originalSource: string;
  fontSize: number;
  refresh: () => void;
  attachToChat: (attachment: ChatAttachment) => void;
}) {
  const editor = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    selection: string;
    startLine: number;
    endLine: number;
  } | null>(null);
  const value =
    props.translation ||
    "La traduccion aparecera aqui despues de usar Traducir codigo (F9).";

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

  function openContextMenu(event: React.MouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    const selection = editor.current?.getSelection();
    const model = editor.current?.getModel();
    const selectedText = selection && model ? model.getValueInRange(selection).trim() : "";
    const width = 248;
    const height = 82;
    setContextMenu({
      x: Math.min(event.clientX, window.innerWidth - width - 8),
      y: Math.min(event.clientY, window.innerHeight - height - 8),
      selection: selectedText,
      startLine: selection?.startLineNumber ?? 1,
      endLine: selection?.endLineNumber ?? 1,
    });
  }

  function explainSelection() {
    if (!contextMenu?.selection) return;
    const encoded = new TextEncoder().encode(contextMenu.selection);
    const lines = contextMenu.startLine === contextMenu.endLine
      ? `linea ${contextMenu.startLine}`
      : `lineas ${contextMenu.startLine}-${contextMenu.endLine}`;
    props.attachToChat({
      id: `translation-${crypto.randomUUID()}`,
      name: `Traduccion seleccionada (${lines})`,
      kind: "text",
      mediaType: "text/plain",
      content: contextMenu.selection,
      size: encoded.byteLength,
      truncated: false,
      selectionContext: {
        sourceName: `Traduccion de ${props.sourceName}`,
        language: "miezee-educativo",
        startLine: contextMenu.startLine,
        endLine: contextMenu.endLine,
        fullSource: props.translation,
        relatedPythonSource: props.originalSource,
      },
    });
    setContextMenu(null);
  }

  return (
    <section
      className="translation-view"
      aria-label="Traduccion de solo lectura"
      onContextMenu={openContextMenu}
    >
      <header className="translation-header">
        <FileCode2 size={15} />
        <span>Codigo Miezee traducido</span>
        <span className="translation-readonly">
          <LockKeyhole size={12} />
          Solo lectura
        </span>
      </header>
      <div className="translation-editor">
        <Editor
          path="miezee-translation://resultado.miezee"
          language={LANGUAGE_ID}
          theme="vs-dark"
          value={value}
          onMount={(instance) => {
            editor.current = instance;
          }}
          options={{
            automaticLayout: true,
            readOnly: true,
            domReadOnly: true,
            fontSize: props.fontSize,
            lineNumbers: "on",
            lineNumbersMinChars: 3,
            glyphMargin: false,
            folding: false,
            minimap: { enabled: false },
            renderLineHighlight: "none",
            overviewRulerLanes: 0,
            hideCursorInOverviewRuler: true,
            scrollBeyondLastLine: false,
            contextmenu: false,
            padding: { top: 10, bottom: 10 },
            wordWrap: "off",
          }}
        />
      </div>
      {contextMenu && (
        <div
          className="translation-context-menu"
          role="menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onPointerDown={(event) => event.stopPropagation()}
        >
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setContextMenu(null);
              props.refresh();
            }}
          >
            <RefreshCw size={15} />
            <span>Actualizar</span>
          </button>
          <button
            type="button"
            role="menuitem"
            disabled={!contextMenu.selection}
            title={contextMenu.selection ? "Cargar la seleccion en el chat" : "Selecciona texto para cargarlo"}
            onClick={explainSelection}
          >
            <MessageCircleQuestion size={15} />
            <span>¿Que hace, para que sirve?</span>
          </button>
        </div>
      )}
    </section>
  );
}
