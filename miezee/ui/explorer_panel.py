from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from miezee.services.file_service import FileService


class ExplorerPanel(QWidget):
    open_requested = Signal(str)
    new_requested = Signal()

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Proyecto")
        self.new_button = QPushButton("Nuevo archivo")
        self.refresh_button = QPushButton("Actualizar")
        layout.addWidget(self.new_button)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.tree)
        self.new_button.clicked.connect(self.new_requested.emit)
        self.refresh_button.clicked.connect(self.refresh)
        self.tree.itemDoubleClicked.connect(self._open_item)
        self.refresh()

    def set_root(self, root: Path) -> None:
        self.root = root
        self.refresh()

    def refresh(self) -> None:
        self.tree.clear()
        root_item = QTreeWidgetItem([self.root.name or str(self.root)])
        self.tree.addTopLevelItem(root_item)
        groups: dict[str, QTreeWidgetItem] = {}
        for path in FileService.project_files(self.root) if self.root.exists() else []:
            group_name = self._group_name_for(path)
            parent = groups.get(group_name)
            if parent is None:
                parent = QTreeWidgetItem([group_name])
                groups[group_name] = parent
                root_item.addChild(parent)
            item = QTreeWidgetItem([path.name])
            item.setData(0, 1, str(path))
            parent.addChild(item)
        self.tree.expandAll()

    def _group_name_for(self, path: Path) -> str:
        if path.suffix.lower() == ".py":
            return "Python (.py)"
        if path.suffix.lower() == ".miezee":
            return "Miezee (.miezee)"
        return "Datos y documentos"

    def add_open_file(self, path: str) -> None:
        # Los archivos abiertos ya se muestran en las pestanas superiores.
        return

    def _open_item(self, item: QTreeWidgetItem) -> None:
        path = item.data(0, 1)
        if path:
            self.open_requested.emit(path)
