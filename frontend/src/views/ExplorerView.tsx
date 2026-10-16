import { useState } from "react";
import {
  FileCode2,
  FileText,
  Folder,
  FilePlus2,
  RefreshCw,
  FolderOpen,
} from "lucide-react";

interface Tree {
  files: { name: string; path: string }[];
  folders: Record<string, Tree>;
}
export function ExplorerView(props: {
  root?: string;
  files: { name: string; path: string }[];
  open: (path: string) => void;
  refresh: () => void;
  create: () => void;
  openFolder: () => void;
}) {
  const [filter, setFilter] = useState("all");
  const tree: Tree = { files: [], folders: {} };
  for (const file of props.files) {
    if (filter !== "all" && !file.name.toLowerCase().endsWith(filter)) continue;
    const relative = file.path
      .replace(/\\/g, "/")
      .slice((props.root?.replace(/\\/g, "/").length ?? 0) + 1)
      .split("/");
    let node = tree;
    for (const folder of relative.slice(0, -1))
      node = node.folders[folder] ??= { files: [], folders: {} };
    node.files.push(file);
  }
  function render(node: Tree) {
    return (
      <>
        {Object.entries(node.folders).map(([name, child]) => (
          <details key={name} open>
            <summary>
              <Folder size={14} />
              {name}
            </summary>
            <div className="tree-children">{render(child)}</div>
          </details>
        ))}
        {node.files.map((file) => (
          <button
            key={file.path}
            onClick={() => props.open(file.path)}
            title={file.path}
          >
            {file.name.endsWith(".py") ? (
              <FileCode2 size={15} />
            ) : (
              <FileText size={15} />
            )}
            <span>{file.name}</span>
          </button>
        ))}
      </>
    );
  }
  return (
    <>
      <header className="panel-title">
        <span>EXPLORADOR</span>
        <div className="panel-tools">
          <button title="Nuevo archivo" onClick={props.create}>
            <FilePlus2 size={15} />
          </button>
          <button title="Abrir carpeta" onClick={props.openFolder}>
            <FolderOpen size={15} />
          </button>
          <button title="Actualizar" onClick={props.refresh}>
            <RefreshCw size={15} />
          </button>
        </div>
      </header>
      <select
        className="file-filter"
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
        aria-label="Filtro de archivos"
      >
        <option value="all">Todos los archivos</option>
        <option value=".py">Python (.py)</option>
        <option value=".miezee">Miezee (.miezee)</option>
        <option value=".txt">Texto (.txt)</option>
        <option value=".md">Markdown (.md)</option>
        <option value=".json">JSON</option>
        <option value=".csv">CSV</option>
        <option value=".rtf">RTF</option>
      </select>
      <div className="folder-name" title={props.root}>
        {props.root?.split(/[\\/]/).pop() || "examples"}
      </div>
      <nav className="file-list">{render(tree)}</nav>
    </>
  );
}
