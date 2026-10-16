import type { Analysis } from "../models/ide";

interface Props {
  analysis: Analysis | null;
  goToLine: (line: number) => void;
}

const statusText = {
  ok: "Correcto",
  error: "Con errores",
  not_run: "No ejecutado por errores lexicos",
};

export function SyntaxAnalysisView({ analysis, goToLine }: Props) {
  if (!analysis)
    return <p className="empty-analysis">Analiza el archivo para visualizar su estructura sintactica.</p>;

  const { syntax } = analysis;
  const summary = syntax.summary;
  const constructs = Object.entries(summary.constructs ?? {}).sort(([left], [right]) =>
    left.localeCompare(right),
  );
  return (
    <div className="phase-report">
      <header className="phase-summary">
        <strong>Analisis sintactico</strong>
        <span className={syntax.ok ? "phase-ok" : "phase-error"}>{statusText[syntax.status]}</span>
      </header>
      {syntax.errors.length > 0 && (
        <div className="phase-errors" role="alert">
          {syntax.errors.map((error, index) => (
            <button key={`${error.line}-${index}`} onClick={() => goToLine(error.line)}>
              {error.code}, linea {error.line}, columna {error.column ?? 1}: {error.explanation}
            </button>
          ))}
        </div>
      )}
      {syntax.status === "not_run" && (
        <p className="empty-analysis">Corrige primero los errores lexicos para construir el AST.</p>
      )}
      {syntax.ok && (
        <>
          <dl className="syntax-metrics">
            <div><dt>Raiz</dt><dd>{summary.root ?? "Module"}</dd></div>
            <div><dt>Nodos</dt><dd>{summary.nodeCount ?? 0}</dd></div>
            <div><dt>Sentencias</dt><dd>{summary.statementCount ?? 0}</dd></div>
            <div><dt>Expresiones</dt><dd>{summary.expressionCount ?? 0}</dd></div>
          </dl>
          <section className="syntax-section">
            <h3>Construcciones detectadas</h3>
            {constructs.length ? (
              <div className="construct-list">
                {constructs.map(([name, count]) => <span key={name}><code>{name}</code> {count}</span>)}
              </div>
            ) : <p>Ninguna construccion.</p>}
          </section>
          <section className="syntax-section syntax-tree-section">
            <h3>Arbol de sintaxis abstracta (AST)</h3>
            <pre className="syntax-tree">{syntax.tree || "AST vacio"}</pre>
          </section>
        </>
      )}
    </div>
  );
}
