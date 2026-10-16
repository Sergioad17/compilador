export interface Analysis {
  ok: boolean;
  errors: {
    code: string;
    line: number;
    instruction?: string;
    explanation: string;
    suggestion: string;
    rule: string;
  }[];
  symbols: { name: string; type: string; line: number; kind: string }[];
  rules: string[];
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
  | "Consola"
  | "Tabla de simbolos"
  | "Traduccion"
  | "Vista previa";
export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}
export interface Preferences {
  theme: "Default" | "Morado";
  fontSize: number;
  url: string;
  model: string;
}
