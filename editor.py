import sys
import json
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QListWidget, QGraphicsView, 
                             QGraphicsScene, QGraphicsItem, QGraphicsObject, QGraphicsPathItem, 
                             QHBoxLayout, QVBoxLayout, QSplitter, QAction, QFileDialog, QFormLayout, 
                             QLineEdit, QSpinBox, QLabel, QListWidgetItem, QMessageBox, QCheckBox)
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QDrag, QFont
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QMimeData

# --- Tento slovník bude načten ze serveru ---
NODE_DEFINITIONS = {}
SERVER_URL = "http://localhost:5001"

# --- Grafické prvky ---

class Socket(QGraphicsObject):
    """ Grafický prvek pro vstupní/výstupní port bloku """
    def __init__(self, parent, name, is_output=False):
        super().__init__(parent)
        self.parent_block, self.socket_name, self.is_output = parent, name, is_output
        self.radius = 6
        self.setAcceptHoverEvents(True)
        self.connections = []

    def boundingRect(self):
        return QRectF(-self.radius, -self.radius, 2 * self.radius, 2 * self.radius)

    def paint(self, painter, option, widget=None):
        painter.setBrush(QBrush(QColor("#ecf0f1")))
        painter.setPen(QPen(QColor("#95a5a6"), 1))
        painter.drawEllipse(int(-self.radius), int(-self.radius), int(2 * self.radius), int(2 * self.radius))

    def get_scene_pos(self):
        return self.mapToScene(0, 0)
        
    def add_connection(self, conn):
        self.connections.append(conn)
        
    def remove_connection(self, conn):
        if conn in self.connections:
            self.connections.remove(conn)

class Connection(QGraphicsPathItem):
    """ Grafická reprezentace spojení mezi dvěma sockety """
    def __init__(self, start_socket, end_socket=None):
        super().__init__()
        self.start_socket, self.end_socket = start_socket, end_socket
        self.start_socket.add_connection(self)
        if self.end_socket: self.end_socket.add_connection(self)
        self.setPen(QPen(QColor("#ecf0f1"), 2)); self.setZValue(-1)
        self.last_end_pos = start_socket.get_scene_pos() 

    def update_path(self, end_pos=None):
        if end_pos: self.last_end_pos = end_pos
        p1 = self.start_socket.get_scene_pos()
        p2 = self.end_socket.get_scene_pos() if self.end_socket else self.last_end_pos
        path = QPainterPath(); path.moveTo(p1)
        dx = p2.x() - p1.x()
        ctrl1, ctrl2 = QPointF(p1.x() + dx * 0.5, p1.y()), QPointF(p1.x() + dx * 0.5, p2.y())
        path.cubicTo(ctrl1, ctrl2, p2); self.setPath(path)

    def set_end_socket(self, socket):
        self.end_socket = socket
        if self.end_socket: self.end_socket.add_connection(self)

class Block(QGraphicsObject):
    """ Grafická reprezentace funkčního bloku """
    doubleClicked = pyqtSignal(object)
    
    def __init__(self, block_type, data=None):
        super().__init__()
        self.block_type, self.data, self.def_ = block_type, data or {}, NODE_DEFINITIONS[block_type]
        self.width, self.height = 180, 40
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsScenePositionChanges)
        
        self.inputs, self.outputs, y_pos_in, y_pos_out = [], [], 35, 35
        for name in self.def_['inputs']:
            self.inputs.append(Socket(self, name, is_output=False)); self.inputs[-1].setPos(0, y_pos_in); y_pos_in += 20
        for name in self.def_['outputs']:
            self.outputs.append(Socket(self, name, is_output=True)); self.outputs[-1].setPos(self.width, y_pos_out); y_pos_out += 20
        
        self.height = max(y_pos_in - 15, y_pos_out - 15, self.height)
        self.update_id_display()

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        
        path_body = QPainterPath(); path_body.addRoundedRect(0, 0, self.width, self.height, 8, 8)
        painter.setBrush(QBrush(QColor(self.def_.get('color', '#34495e'))))
        pen = QPen(QColor(Qt.black), 1.5)
        if self.isSelected():
            pen.setColor(QColor("#3498db")); pen.setWidth(3)
        painter.setPen(pen); painter.drawPath(path_body)

        path_header = QPainterPath(); path_header.addRoundedRect(0, 0, self.width, 25, 8, 8)
        path_header.addRect(0, 15, self.width, 10) 
        painter.setBrush(QBrush(QColor(0, 0, 0, 50))); painter.setPen(Qt.NoPen); painter.drawPath(path_header)
        
        painter.setPen(Qt.white); painter.setFont(QFont("Arial", 9, QFont.Bold))
        painter.drawText(QRectF(0, 0, self.width, 25), Qt.AlignCenter, self.def_['title'])
        
        painter.setFont(QFont("Arial", 8, QFont.Normal)); painter.setPen(QColor("#dddddd"))
        painter.drawText(QRectF(5, 28, self.width - 10, 15), Qt.AlignLeft, self.id_text)
        
        painter.setFont(QFont("Arial", 8, QFont.Normal)); painter.setPen(Qt.white)
        for s in self.inputs:
            painter.drawText(QRectF(s.pos().x() + s.radius + 5, s.pos().y() - 10, self.width/2 - 20, 20), Qt.AlignLeft | Qt.AlignVCenter, s.socket_name)
        for s in self.outputs:
            painter.drawText(QRectF(s.pos().x() - (self.width/2 - 5) - 10, s.pos().y() - 10, self.width/2 - 5, 20), Qt.AlignRight | Qt.AlignVCenter, s.socket_name)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for s in self.inputs + self.outputs:
                for conn in s.connections: conn.update_path()
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit(self); super().mouseDoubleClickEvent(event)
        
    def update_id_display(self):
        self.id_text = f"ID: {self.data.get('id', '(nenastaveno)')}"; self.update()

class NodeScene(QGraphicsScene):
    """ Scéna pro správu bloků a spojení - s opravou pro spojování """
    def __init__(self, parent=None):
        super().__init__(parent); self.temp_connection = None
        
    def mousePressEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if event.button() == Qt.LeftButton and isinstance(item, Socket) and item.is_output:
            self.temp_connection = Connection(item); self.addItem(self.temp_connection)
        else:
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event):
        if self.temp_connection:
            self.temp_connection.update_path(event.scenePos())
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        if self.temp_connection:
            start_socket = self.temp_connection.start_socket
            item_at_release = self.itemAt(event.scenePos(), self.views()[0].transform())
            
            if isinstance(item_at_release, Socket) and not item_at_release.is_output and item_at_release.parent_block != start_socket.parent_block:
                self.temp_connection.set_end_socket(item_at_release); self.temp_connection.update_path()
            else:
                start_socket.remove_connection(self.temp_connection); self.removeItem(self.temp_connection)
            
            self.temp_connection = None
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            for item in self.selectedItems():
                if isinstance(item, Block):
                    for s in list(item.inputs) + list(item.outputs):
                        for conn in list(s.connections):
                            conn.start_socket.remove_connection(conn)
                            if conn.end_socket: conn.end_socket.remove_connection(conn)
                            self.removeItem(conn)
                    self.removeItem(item)
        else:
            super().keyPressEvent(event)

class NodeView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent); self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag); self.setAcceptDrops(True)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('text/plain'): event.acceptProposedAction()
        
    def dragMoveEvent(self, event):
        event.acceptProposedAction()
        
    def dropEvent(self, event):
        block_type = event.mimeData().text()
        if block_type in NODE_DEFINITIONS:
            block = Block(block_type); self.scene().addItem(block)
            block.setPos(self.mapToScene(event.pos())); event.acceptProposedAction()

class BlockListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.setDragEnabled(True)
        
    def populate(self, definitions):
        self.clear()
        for name, definition in sorted(definitions.items(), key=lambda item: item[1]['title']):
            item = QListWidgetItem(definition['title']); item.setData(Qt.UserRole, name)
            self.addItem(item)
            
    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item:
            mime_data = QMimeData(); mime_data.setText(item.data(Qt.UserRole))
            drag = QDrag(self); drag.setMimeData(mime_data); drag.exec_(Qt.CopyAction)

class PropertiesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.current_block = None
        self.layout = QVBoxLayout(self); self.placeholder = QLabel("Dvojklikem na blok zobrazíte jeho nastavení.")
        self.layout.addWidget(self.placeholder); self.form_widget = QWidget()
        self.layout.addWidget(self.form_widget); self.layout.addStretch()

    def show_properties(self, block):
        self.current_block = block; self.placeholder.hide()
        old_layout = self.form_widget.layout()
        if old_layout is not None: QWidget().setLayout(old_layout)
            
        form_layout = QFormLayout(); self.form_widget.setLayout(form_layout)
        title = QLabel(f"<b>Nastavení: {block.def_['title']}</b>"); form_layout.addRow(title)
        
        id_edit = QLineEdit(block.data.get('id', ''))
        id_edit.setPlaceholderText(f"{block.block_type.lower()}_{block.scenePos().toPoint().x()}")
        id_edit.textChanged.connect(lambda text: self.update_data('id', text)); form_layout.addRow("ID bloku:", id_edit)

        for field in block.def_['fields']:
            val = block.data.get(field['name'])
            
            if field['type'] == 'int':
                widget = QSpinBox(); widget.setRange(-10000, 10000)
                widget.setValue(int(val) if val is not None and str(val).lstrip('-').isdigit() else 0)
                widget.valueChanged.connect(lambda v, n=field['name']: self.update_data(n, v))
            elif field['type'] == 'bool':
                widget = QCheckBox()
                widget.setChecked(bool(val) if val is not None else False)
                widget.stateChanged.connect(lambda state, n=field['name']: self.update_data(n, bool(state)))
            else: 
                widget = QLineEdit(str(val) if val is not None else ""); widget.setPlaceholderText(field.get('placeholder', ''))
                widget.textChanged.connect(lambda text, n=field['name']: self.update_data(n, text))
            form_layout.addRow(field['label'] + ":", widget)

    def update_data(self, key, value):
        if self.current_block:
            field_def = next((f for f in self.current_block.def_['fields'] if f['name'] == key), None)
            if field_def and field_def['type'] == 'float':
                try: value = float(value)
                except (ValueError, TypeError): pass
            self.current_block.data[key] = value
            if key == 'id': self.current_block.update_id_display()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Vizuální Konfigurátor"); self.setGeometry(100, 100, 1200, 700)
        
        generate_action = QAction("Vygenerovat a Uložit config.json", self); generate_action.triggered.connect(self.generate_and_save_json)
        exit_action = QAction("Ukončit", self); exit_action.triggered.connect(self.close)
        menu_bar = self.menuBar(); file_menu = menu_bar.addMenu("Soubor")
        file_menu.addAction(generate_action); file_menu.addSeparator(); file_menu.addAction(exit_action)
        
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget); self.block_list = BlockListWidget()
        self.scene = NodeScene(); self.view = NodeView(self.scene); self.properties_panel = PropertiesPanel()
        
        splitter = QSplitter(Qt.Horizontal); splitter.addWidget(self.block_list); splitter.addWidget(self.view); splitter.addWidget(self.properties_panel)
        splitter.setSizes([200, 800, 250]); main_layout.addWidget(splitter)
        
        self.scene.selectionChanged.connect(self.on_selection_changed)
        self.load_definitions()

    def load_definitions(self):
        global NODE_DEFINITIONS
        try:
            response = requests.get(f"{SERVER_URL}/api/block-definitions", timeout=3)
            response.raise_for_status()
            NODE_DEFINITIONS = response.json()
            if not NODE_DEFINITIONS:
                raise ValueError("Server vrátil prázdný seznam definic.")
            self.block_list.populate(NODE_DEFINITIONS)
            self.statusBar().showMessage("Definice bloků úspěšně načteny ze serveru.", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Chyba Spojení", f"Nepodařilo se načíst definice bloků ze serveru.\n{e}\n\nUjistěte se, že backend běží na {SERVER_URL} a že Lua soubory mají správně formátované @blockinfo hlavičky.")
            self.close()

    def on_selection_changed(self):
        items = self.scene.selectedItems()
        if len(items) == 1 and isinstance(items[0], Block):
            items[0].doubleClicked.connect(self.properties_panel.show_properties)
        else:
            self.properties_panel.current_block = None; self.properties_panel.placeholder.show()
            old_layout = self.properties_panel.form_widget.layout()
            if old_layout is not None: QWidget().setLayout(old_layout)

    def generate_and_save_json(self):
        config = {"mqtt_broker_host": "localhost", "mqtt_broker_port": 1883, "blocks": []}
        blocks_on_scene = [item for item in self.scene.items() if isinstance(item, Block)]
        id_map = {block: i for i, block in enumerate(blocks_on_scene)}
        
        unique_ids = set()
        for block_item in blocks_on_scene:
            id_ = block_item.data.get('id', '').strip()
            if not id_: id_ = f"{block_item.block_type.lower()}_{id_map[block_item]+1}"
            
            if id_ in unique_ids:
                 QMessageBox.warning(self, "Chyba Validace", f"ID bloku '{id_}' není unikátní!"); return
            unique_ids.add(id_)
            
            block_dict = {"id": id_, "type": block_item.block_type, "lua_script": block_item.def_['lua']}
            
            config_data = {}
            for key, val in block_item.data.items():
                if key != 'id' and val != '':
                    field_def = next((f for f in block_item.def_['fields'] if f['name'] == key), None)
                    if field_def:
                        try:
                            if field_def['type'] == 'int': val = int(val)
                            elif field_def['type'] == 'float': val = float(val)
                        except (ValueError, TypeError): pass
                    config_data[key] = val
            if config_data: block_dict["config"] = config_data
            
            inputs, outputs = {}, {}
            for socket in block_item.outputs: outputs[socket.socket_name] = f"smarthome/{id_}/{socket.socket_name}"
            for socket in block_item.inputs:
                for conn in socket.connections:
                    if conn.end_socket == socket:
                        source_socket, source_block = conn.start_socket, conn.start_socket.parent_block
                        source_id_val = source_block.data.get('id', '').strip()
                        if not source_id_val: source_id_val = f"{source_block.block_type.lower()}_{id_map[source_block]+1}"
                        inputs[socket.socket_name] = {"source_block_id": source_id_val, "source_output": source_socket.socket_name}
            
            if inputs: block_dict["inputs"] = inputs
            if outputs: block_dict["outputs"] = outputs
            config["blocks"].append(block_dict)
        
        path, _ = QFileDialog.getSaveFileName(self, "Uložit konfigurační soubor", "", "JSON Files (*.json)")
        if path:
            if not path.endswith('.json'): path += '.json'
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                QMessageBox.information(self, "Úspěch", f"Konfigurace byla úspěšně uložena do:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Chyba", f"Chyba při ukládání souboru: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())