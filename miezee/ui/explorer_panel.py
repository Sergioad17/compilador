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
        self.tree.setHeaderLabel("Miezee")
        self.new_button = QPushButton("Nuevo archivo")
        self.refresh_button = QPushButton("Actualizar")
        layout.addWidget(self.new_button)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.tree)
        self.new_button.clicked.connect(self.new_requested.emit)
        self.refresh_button.clicked.connect(self.refresh)
        self.tree.itemDoubleClicked.connect(self._open_item)
        self.refresh()

    def refresh(self) -> None:
        self.tree.clear()
        files_root = QTreeWidgetItem(["Archivos .miezee"])
        tests_root = QTreeWidgetItem(["Casos de prueba"])
        self.tree.addTopLevelItem(files_root)
        self.tree.addTopLevelItem(tests_root)
        for path in FileService.miezee_files(self.root):
            parent = tests_root if "examples" in path.parts else files_root
            item = QTreeWidgetItem([path.name])
            item.setData(0, 1, str(path))
            parent.addChild(item)
        self.tree.expandAll()

    def add_open_file(self, path: str) -> None:
        # Los archivos abiertos ya se muestran en las pestanas superiores.
        return

    def _open_item(self, item: QTreeWidgetItem) -> None:
        path = item.data(0, 1)
        if path:
            self.open_requested.emit(path)
