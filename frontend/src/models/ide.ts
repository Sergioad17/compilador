export interface Analysis {
  ok: boolean;
  errors: {
    code: string;
    line: number;
    column?: number;
    endLine?: number | null;
    endColumn?: number | null;
    instruction?: string;
    explanation: string;
    suggestion: string;
    rule: string;
  }[];
  symbols: { name: string; type: string; line: number; kind: string }[];
  rules: string[];
  lexical: {
    ok: boolean;
    status: "ok" | "error";
    tokenCount: number;
    errors: Analysis["errors"];
  };
  syntax: {
    ok: boolean;
    status: "ok" | "error" | "not_run";
    errors: Analysis["errors"];
    summary: Partial<{
      root: string;
      nodeCount: number;
      statementCount: number;
      expressionCount: number;
      constructs: Record<string, number>;
    }>;
    tree: string;
  };
  tokens?: {
    type: string;
    category: string;
    exactType: string;
    lexeme: string;
    line: number;
    column: number;
    endLine: number;
    endColumn: number;
  }[];
  semantic: {
    ok: boolean;
    status: "ok" | "error" | "not_run";
    checks: string[];
    scopes: {
      name: string;
      type: string;
      line: number;
      identifiers: { name: string; roles: string[] }[];
    }[];
    warnings: Analysis["errors"];
  };
}
export interface IntermediateCode {
  ok: boolean;
  text: string;
  instructions: { op: string; arg1: string; arg2: string; result: string; line: number }[];
  errors?: Analysis["errors"];
  metadata?: {
    format: "TAC";
    version: number;
    sourceLanguage: "Python";
    sourceLines: number;
    instructionCount: number;
  };
}
export interface Document {
  id: string;
  name: string;
  source: string;
  path?: string;
  savedSource?: string;
  replacedPaths?: string[];
}
export type Panel =
  | "Problemas"
  | "Resultado"
  | "Lexico"
  | "Sintactico"
  | "Consola"
  | "Tabla de simbolos"
  | "Traduccion"
  | "Semantico"
  | "Codigo intermedio"
  | "Vista previa";
export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  attachments?: string[];
}
export interface ChatAttachment {
  id: string;
  name: string;
  kind: "text" | "image";
  mediaType: string;
  content: string;
  size: number;
  truncated: boolean;
  selectionContext?: {
    sourceName: string;
    language: "python" | "miezee-educativo";
    startLine: number;
    endLine: number;
    fullSource: string;
    relatedPythonSource?: string;
  };
}
export interface Preferences {
  theme: "Default" | "Morado";
  fontSize: number;
  url: string;
  model: string;
}

export type AIStatusKind =
  | "checking"
  | "ready"
  | "working"
  | "missing"
  | "offline"
  | "disconnected";
