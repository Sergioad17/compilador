import { useEffect, useRef } from "react";
import {
  FileCode2,
  X,
  SearchCheck,
  Languages,
  MessageSquare,
  Play,
  Square,
  PanelBottom,
  Folder,
  Eye,
  Binary,
} from "lucide-react";
import { useIdeController } from "./controllers/useIdeController";
import { useLayoutController } from "./controllers/useLayoutController";
import { CodeEditor } from "./views/CodeEditor";
import { ConsoleView } from "./views/ConsoleView";
import { ChatView } from "./views/ChatView";
import { ExplorerView } from "./views/ExplorerView";
import { HoverMenu } from "./views/HoverMenu";
import { WindowControls } from "./views/WindowControls";
import { SettingsView } from "./views/SettingsView";
import { LexicalAnalysisView } from "./views/LexicalAnalysisView";
import { SyntaxAnalysisView } from "./views/SyntaxAnalysisView";
import { AIStatusIndicator } from "./views/AIStatusIndicator";
import { CommandPalette, type Action } from "./views/CommandPalette";
import {
  closeWindow,
  setWindowIcon,
  guardWindowClose,
} from "./services/window";
import { backend } from "./services/backend";
import { isTauri } from "@tauri-apps/api/core";
import type { Panel } from "./models/ide";
import logo from "./assets/miezee.png";
import purpleLogo from "./assets/purple_miezee.png";
import "./styles.css";

const panels: Panel[] = [
  "Traduccion",
  "Problemas",
  "Resultado",
  "Lexico",
  "Sintactico",
  "Consola",
  "Tabla de simbolos",
  "Semantico",
  "Codigo intermedio",
  "Vista previa",
];
export function App() {
  const ide = useIdeController();
  const layout = useLayoutController();
  const latest = useRef(ide);
  latest.current = ide;
  useEffect(() => {
    let disposed = false;
    let unlisten: (() => void) | undefined;
    void guardWindowClose(
      async () =>
        !latest.current.documents.some(
          (d) => d.source !== (d.savedSource ?? ""),
        ) || (await backend.confirmClose()),
      async () => {
        latest.current.chat.stop();
        await backend.stop();
      },
    )
      .then((stop) => {
        if (disposed) stop();
        else unlisten = stop;
      })
      .catch(console.error);
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (
        !isTauri() &&
        latest.current.documents.some((d) => d.source !== (d.savedSource ?? ""))
      ) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", beforeUnload);
    return () => {
      disposed = true;
      unlisten?.();
      window.removeEventListener("beforeunload", beforeUnload);
    };
  }, []);
  const icon = ide.preferences.theme === "Morado" ? purpleLogo : logo;
  useEffect(() => {
    void setWindowIcon(icon).catch(console.error);
  }, [icon]);
  useEffect(() => {
    function closeMenus(event: MouseEvent) {
      if (!(event.target as Element).closest(".menubar"))
        document
          .querySelectorAll(".menubar details[open]")
          .forEach((menu) => menu.removeAttribute("open"));
    }
    document.addEventListener("click", closeMenus);
    return () => document.removeEventListener("click", closeMenus);
  }, []);
  function show(panel: Panel) {
    ide.setPanel(panel);
    if (!ide.visibility.bottom) ide.toggle("bottom");
  }
  function explain() {
    const error =
      ide.analysis?.errors.find((error) => error.line === ide.line?.number) ??
      ide.analysis?.errors[0];
    if (!ide.visibility.chat) ide.toggle("chat");
    void ide.chat.send(
      error
        ? `/explicar Explica ${error.code} en linea ${error.line}: ${error.explanation}. Codigo: ${ide.active.source}`
        : "/explicar explica el codigo del archivo actual: " +
            ide.active.source,
    );
  }
  const menus: Record<string, Action[]> = {
    Archivo: [
      { name: "Nuevo archivo", shortcut: "Ctrl+N", run: ide.create },
      {
        name: "Abrir archivo",
        shortcut: "Ctrl+O",
        run: () => {
          void ide.fileAction("open");
        },
      },
      {
        name: "Abrir carpeta",
        shortcut: "Ctrl+K",
        run: () => {
          void ide.fileAction("folder");
        },
      },
      {
        name: "Guardar",
        shortcut: "Ctrl+S",
        run: () => {
          void ide.fileAction("save");
        },
      },
      {
        name: "Guardar como",
        shortcut: "Ctrl+Shift+S",
        run: () => {
          void ide.fileAction("saveAs");
        },
      },
      {
        name: "Salir",
        run: () => {
          void closeWindow();
        },
      },
    ],
    Editar: [
      { name: "Limpiar resultados", shortcut: "Ctrl+L", run: ide.clear },
      {
        name: "Cambiar tamano de fuente",
        run: () => ide.setSettingsOpen(true),
      },
    ],
    Ver: [
      {
        name: "Mostrar vista previa",
        shortcut: "F7",
        run: () => {
          void ide.run(true);
        },
      },
      {
        name: "Mostrar tabla de simbolos",
        run: () => show("Tabla de simbolos"),
      },
      {
        name: "Mostrar analisis lexico",
        run: () => { void ide.perform("lexical"); },
      },
      {
        name: "Mostrar analisis sintactico",
        run: () => { void ide.perform("syntax"); },
      },
      {
        name: "Mostrar analisis semantico",
        run: () => { void ide.perform("semantic"); },
      },
      {
        name: "Mostrar u ocultar chat",
        shortcut: "Ctrl+Shift+C",
        run: () => ide.toggle("chat"),
      },
      {
        name: "Mostrar u ocultar explorador",
        shortcut: "Ctrl+B",
        run: () => ide.toggle("explorer"),
      },
      {
        name: "Mostrar u ocultar panel inferior",
        shortcut: "Ctrl+J",
        run: () => ide.toggle("bottom"),
      },
    ],
    Ejecutar: [
      {
        name: "Analizar",
        shortcut: "F5",
        run: () => {
          void ide.perform("analyze");
        },
      },
      {
        name: "Ejecutar programa",
        shortcut: "F6",
        run: () => {
          void ide.run();
        },
      },
      {
        name: "Traducir codigo",
        shortcut: "F9",
        run: () => {
          void ide.perform("translate");
        },
      },
      {
        name: "Generar codigo intermedio",
        shortcut: "F10",
        run: () => { void ide.perform("intermediate"); },
      },
      {
        name: "Detener programa",
        run: () => {
          void ide.terminal.stop();
        },
      },
    ],
    Terminal: [
      { name: "Mostrar consola", shortcut: "F8", run: () => show("Consola") },
      {
        name: "Ejecutar en consola",
        run: () => {
          void ide.run();
        },
      },
      { name: "Limpiar consola", run: ide.terminal.clear },
    ],
    Ayuda: [
      { name: "Configuracion", run: () => ide.setSettingsOpen(true) },
      { name: "Explicar error seleccionado con IA", run: explain },
      {
        name: "Paleta de comandos",
        shortcut: "Ctrl+Shift+P",
        run: () => ide.setPaletteOpen(true),
      },
    ],
  };
  return (
    <main
      className={`app-shell ${ide.preferences.theme === "Morado" ? "theme-purple" : ""}`}
    >
      <header className="app-header" data-tauri-drag-region>
        <img src={icon} alt="" data-tauri-drag-region draggable={false} />
        <strong data-tauri-drag-region>Miezee IDE</strong>
        <nav className="menubar">
          {Object.entries(menus).map(([name, actions]) => (
            <HoverMenu key={name} label={name}>
              <div className="menu">
                {actions.map((action) => (
                  <button
                    key={action.name}
                    onClick={(event) => {
                      event.currentTarget
                        .closest("details")
                        ?.removeAttribute("open");
                      action.run();
                    }}
                  >
                    {action.name}
                    <kbd>{action.shortcut}</kbd>
                  </button>
                ))}
                {name === "Editar" && (
                  <>
                    <hr />
                    <HoverMenu className="theme-submenu" label="Temas">
                      <div>
                        {(["Default", "Morado"] as const).map((theme) => (
                          <button
                            key={theme}
                            role="menuitemradio"
                            aria-checked={ide.preferences.theme === theme}
                            onClick={() =>
                              ide.setPreferences({ ...ide.preferences, theme })
                            }
                          >
                            <span
                              className={`theme-swatch ${theme.toLowerCase()}`}
                            />
                            {theme}
                            {ide.preferences.theme === theme ? " ✓" : ""}
                          </button>
                        ))}
                      </div>
                    </HoverMenu>
                  </>
                )}
              </div>
            </HoverMenu>
          ))}
        </nav>
        <div className="window-drag-space" data-tauri-drag-region />
        <div className="header-tools">
          <button title="Explorador" onClick={() => ide.toggle("explorer")}>
            <Folder size={16} />
          </button>
          <button title="Panel inferior" onClick={() => ide.toggle("bottom")}>
            <PanelBottom size={17} />
          </button>
          <button title="Chat" onClick={() => ide.toggle("chat")}>
            <MessageSquare size={16} />
          </button>
        </div>
        <WindowControls />
      </header>
      <div
        className={`workbench ${!ide.visibility.explorer ? "hide-explorer" : ""} ${!ide.visibility.chat ? "hide-chat" : ""}`}
        style={{
          gridTemplateColumns: `${ide.visibility.explorer ? `${layout.sizes.explorer}px 4px` : "0px 0px"} minmax(0, 1fr) ${ide.visibility.chat ? `4px ${layout.sizes.chat}px` : "0px 0px"}`,
        }}
      >
        <aside className="sidebar" hidden={!ide.visibility.explorer}>
          <ExplorerView
            root={ide.root}
            files={ide.files}
            create={ide.create}
            refresh={() => {
              void ide.refresh();
            }}
            openFolder={() => {
              void ide.fileAction("folder");
            }}
            open={(path) => {
              void ide.fileAction("open", path);
            }}
          />
        </aside>
        <div
          className="splitter vertical explorer-splitter"
          hidden={!ide.visibility.explorer}
          onPointerDown={(event) => layout.resize("explorer", event)}
        />
        <section
          className="workspace"
          style={{
            gridTemplateRows: `38px minmax(0, 1fr) ${ide.visibility.bottom ? `4px ${layout.sizes.bottom}px` : "0px 0px"}`,
          }}
        >
          <div className="editor-header">
            <nav className="tabs">
              {ide.documents.map((document) => (
                <div
                  key={document.id}
                  className={`tab ${document.id === ide.active.id ? "active" : ""}`}
                >
                  <button
                    onClick={() => ide.select(document.id)}
                    title={document.path ?? document.name}
                  >
                    <FileCode2 size={14} />
                    <span>
                      {document.name}
                      {document.source !== (document.savedSource ?? "")
                        ? " *"
                        : ""}
                    </span>
                  </button>
                  <button
                    title="Cerrar archivo"
                    onClick={() => {
                      void ide.close(document.id);
                    }}
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </nav>
            <div className="editor-tools">
              <button
                title="Analizar (F5)"
                disabled={ide.busy}
                onClick={() => {
                  void ide.perform("analyze");
                }}
              >
                <SearchCheck size={18} />
              </button>
              <button
                title="Ejecutar (F6)"
                disabled={ide.terminal.starting}
                onClick={() => {
                  void ide.run();
                }}
              >
                <Play size={17} />
              </button>
              <button
                title="Detener"
                disabled={!ide.terminal.running}
                onClick={() => {
                  void ide.terminal.stop();
                }}
              >
                <Square size={14} />
              </button>
              <button
                title="Traducir (F9)"
                disabled={ide.busy}
                onClick={() => {
                  void ide.perform("translate");
                }}
              >
                <Languages size={18} />
              </button>
              <button
                title="Generar codigo intermedio (F10)"
                disabled={ide.busy}
                onClick={() => { void ide.perform("intermediate"); }}
              >
                <Binary size={18} />
              </button>
            </div>
          </div>
          <div className="editor-panel">
            <CodeEditor
              id={ide.active.id}
              source={ide.active.source}
              errors={ide.analysis?.errors ?? []}
              onChange={ide.update}
              line={ide.line}
              fontSize={ide.preferences.fontSize}
              onCursorChange={ide.setCursor}
            />
          </div>
          <div
            className="splitter horizontal"
            hidden={!ide.visibility.bottom}
            onPointerDown={(event) => layout.resize("bottom", event)}
          />
          <section className="bottom-panel" hidden={!ide.visibility.bottom}>
            <nav className="panel-tabs">
              {panels.map((panel) => (
                <button
                  key={panel}
                  className={ide.panel === panel ? "active" : ""}
                  onClick={() => show(panel)}
                >
                  {panel}
                  {panel === "Problemas" && ide.analysis
                    ? ` (${ide.analysis.errors.length})`
                    : ""}
                </button>
              ))}
            </nav>
            <div
              className={`panel-content ${ide.panel === "Consola" ? "console-content" : ""}`}
            >
              {ide.notice && (
                <p role="alert" className="notice">
                  {ide.notice}
                </p>
              )}
              {ide.panel === "Problemas" &&
                ide.analysis &&
                (ide.analysis.errors.length ? (
                  <table>
                    <thead>
                      <tr>
                        <th>Codigo</th>
                        <th>Linea</th>
                        <th>Instruccion</th>
                        <th>Descripcion</th>
                        <th>Regla</th>
                        <th>Sugerencia</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ide.analysis.errors.map((error, index) => (
                        <tr
                          key={index}
                          tabIndex={0}
                          onClick={() => ide.goToLine(error.line)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") ide.goToLine(error.line);
                          }}
                        >
                          <td className="error-code">{error.code}</td>
                          <td>{error.line}</td>
                          <td>
                            <code>{error.instruction}</code>
                          </td>
                          <td>{error.explanation}</td>
                          <td>{error.rule}</td>
                          <td>{error.suggestion}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="success">Sin errores detectados.</p>
                ))}
              {ide.panel === "Tabla de simbolos" && ide.analysis && (
                <table>
                  <thead>
                    <tr>
                      <th>Nombre</th>
                      <th>Tipo</th>
                      <th>Linea</th>
                      <th>Clase</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ide.analysis.symbols.map((symbol, index) => (
                      <tr key={index} onClick={() => ide.goToLine(symbol.line)}>
                        <td>{symbol.name}</td>
                        <td>{symbol.type}</td>
                        <td>{symbol.line}</td>
                        <td>{symbol.kind}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {ide.panel === "Resultado" && ide.analysis && (
                <>
                  <p>Estado: {ide.analysis.ok ? "Correcto" : "Con errores"}</p>
                  <p>
                    Reglas aplicadas:{" "}
                    {ide.analysis.rules.join(", ") || "Ninguna"}
                  </p>
                </>
              )}
              {ide.panel === "Lexico" && (
                <LexicalAnalysisView analysis={ide.analysis} goToLine={ide.goToLine} />
              )}
              {ide.panel === "Sintactico" && (
                <SyntaxAnalysisView analysis={ide.analysis} goToLine={ide.goToLine} />
              )}
              {ide.panel === "Semantico" && ide.analysis && (
                <div className="semantic-report">
                  <p className={ide.analysis.semantic.ok ? "success" : "notice"}>
                    Estado semantico: {ide.analysis.semantic.status === "ok" ? "Correcto" : ide.analysis.semantic.status === "error" ? "Con errores" : "No ejecutado por errores previos"}
                  </p>
                  <h3>Validaciones realizadas</h3>
                  <ul>{ide.analysis.semantic.checks.map(check => <li key={check}>{check}</li>)}</ul>
                  {ide.analysis.semantic.warnings.length > 0 && (
                    <><h3>Advertencias</h3><ul>{ide.analysis.semantic.warnings.map((warning, index) => <li key={index}>{warning.code}: {warning.explanation}</li>)}</ul></>
                  )}
                  <h3>Ambitos detectados</h3>
                  <table>
                    <thead><tr><th>Ambito</th><th>Tipo</th><th>Linea</th><th>Identificadores y roles</th></tr></thead>
                    <tbody>{ide.analysis.semantic.scopes.map(scope => (
                      <tr key={scope.name}><td>{scope.name}</td><td>{scope.type}</td><td>{scope.line}</td><td>{scope.identifiers.map(item => `${item.name} (${item.roles.join(", ")})`).join("; ")}</td></tr>
                    ))}</tbody>
                  </table>
                </div>
              )}
              {ide.panel === "Traduccion" && <pre>{ide.translation}</pre>}
              {ide.panel === "Codigo intermedio" && <pre className="intermediate-code">{ide.intermediate?.text || "Genera el codigo intermedio con F10."}</pre>}
              {ide.panel === "Consola" && (
                <ConsoleView
                  {...ide.terminal}
                  submit={(text) => {
                    if (ide.terminal.running) void ide.terminal.input(text);
                    else if (
                      ["run", "ejecutar"].includes(text.trim().toLowerCase())
                    )
                      void ide.run();
                  }}
                  stop={() => {
                    void ide.terminal.stop();
                  }}
                />
              )}
              {ide.panel === "Vista previa" && (
                <div className="preview-view">
                  <button
                    onClick={() => {
                      void ide.run(true);
                    }}
                    disabled={ide.terminal.starting}
                  >
                    <Eye size={17} />
                    Abrir pantalla
                  </button>
                  <pre>{ide.terminal.output}</pre>
                </div>
              )}
            </div>
          </section>
        </section>
        <div
          className="splitter vertical chat-splitter"
          hidden={!ide.visibility.chat}
          onPointerDown={(event) => layout.resize("chat", event)}
        />
        <aside className="assistant" hidden={!ide.visibility.chat}>
          <header className="panel-title">
            <MessageSquare size={16} />
            <span>ASISTENTE</span>
            <AIStatusIndicator
              kind={ide.chat.busy ? "working" : ide.aiStatusKind}
              text={ide.chat.busy ? "Procesando..." : ide.aiStatus}
              detail={
                ide.chat.busy
                  ? `El modelo ${ide.preferences.model} esta generando una respuesta. Espera a que termine o usa Detener.`
                  : ide.aiStatusDetail
              }
            />
          </header>
          <ChatView
            {...ide.chat}
            send={(text, attachments) => {
              void ide.chat.send(text, attachments);
            }}
            explain={explain}
          />
        </aside>
      </div>
      <footer className="statusbar">
        <span>{ide.active.name}</span>
        <span>Python</span>
        <span className="cursor-status">Linea {ide.cursor.line}, Columna {ide.cursor.column}</span>
        <span>
          {ide.busy
            ? "Analizando..."
            : ide.terminal.running
              ? "Ejecutando"
              : ide.analysis
                ? `${ide.analysis.errors.length} errores`
                : "Listo"}
        </span>
        <span className="status-end">UTF-8</span>
        <AIStatusIndicator
          footer
          kind={ide.chat.busy ? "working" : ide.aiStatusKind}
          text={ide.chat.busy ? "Procesando..." : ide.aiStatus}
          detail={
            ide.chat.busy
              ? `El modelo ${ide.preferences.model} esta generando una respuesta. Espera a que termine o usa Detener.`
              : ide.aiStatusDetail
          }
        />
      </footer>
      {ide.settingsOpen && (
        <SettingsView
          value={ide.preferences}
          update={ide.setPreferences}
          close={() => ide.setSettingsOpen(false)}
        />
      )}
      {ide.paletteOpen && (
        <CommandPalette
          actions={Object.values(menus).flat()}
          close={() => ide.setPaletteOpen(false)}
        />
      )}
    </main>
  );
}
