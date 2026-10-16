import type { Analysis } from "../models/ide";

interface Props {
  analysis: Analysis | null;
  goToLine: (line: number) => void;
}

function visibleLexeme(value: string) {
  if (!value) return "(vacio)";
  return value
    .replace(/\\/g, "\\\\")
    .replace(/\r/g, "\\r")
    .replace(/\n/g, "\\n")
    .replace(/\t/g, "\\t");
}

export function LexicalAnalysisView({ analysis, goToLine }: Props) {
  if (!analysis)
    return <p className="empty-analysis">Analiza el archivo para visualizar sus tokens.</p>;

  const tokens = analysis.tokens ?? [];
  return (
    <div className="phase-report">
      <header className="phase-summary">
        <strong>Analisis lexico</strong>
        <span className={analysis.lexical.ok ? "phase-ok" : "phase-error"}>
          {analysis.lexical.ok ? "Correcto" : "Con errores"}
        </span>
        <span>{analysis.lexical.tokenCount} tokens</span>
      </header>
      {analysis.lexical.errors.length > 0 && (
        <div className="phase-errors" role="alert">
          {analysis.lexical.errors.map((error, index) => (
            <button key={`${error.line}-${index}`} onClick={() => goToLine(error.line)}>
              {error.code}, linea {error.line}, columna {error.column ?? 1}: {error.explanation}
            </button>
          ))}
        </div>
      )}
      <div className="analysis-table-wrap">
        <table className="token-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Categoria</th>
              <th>Tipo</th>
              <th>Tipo exacto</th>
              <th>Lexema</th>
              <th>Inicio</th>
              <th>Fin</th>
            </tr>
          </thead>
          <tbody>
            {tokens.map((token, index) => (
              <tr
                key={`${index}-${token.line}-${token.column}`}
                tabIndex={0}
                onClick={() => goToLine(token.line)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") goToLine(token.line);
                }}
              >
                <td>{index + 1}</td>
                <td>{token.category}</td>
                <td>{token.type}</td>
                <td>{token.exactType}</td>
                <td><code>{visibleLexeme(token.lexeme)}</code></td>
                <td>{token.line}:{token.column}</td>
                <td>{token.endLine}:{token.endColumn}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
