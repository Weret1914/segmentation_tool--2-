import sys
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QInputDialog, QMessageBox, QGraphicsView,
    QGraphicsScene, QListWidget
)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QImage, QPainterPath
from PyQt5.QtCore import Qt, QPointF

class AnnotationCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = None
        self.drawing = False
        self.path = QPainterPath()
        self.path_item = None
        self.points = []
        self.scale_factor = 1.0

    def load_image(self, file_path):
        self.image = QPixmap(file_path)
        self.scene.clear()
        self.pixmap_item = self.scene.addPixmap(self.image)
        self.setSceneRect(self.pixmap_item.boundingRect())
        self.points = []
        self.path = QPainterPath()
        if self.path_item:
            self.scene.removeItem(self.path_item)
            self.path_item = None
        self.scale_factor = 1.0
        self.resetTransform()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap_item:
            self.drawing = True
            pos = self.mapToScene(event.pos())
            self.path.moveTo(pos)
            self.points = [pos]
            if self.path_item:
                self.scene.removeItem(self.path_item)
            self.path_item = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drawing:
            pos = self.mapToScene(event.pos())
            self.path.lineTo(pos)
            self.points.append(pos)
            if self.path_item:
                self.scene.removeItem(self.path_item)
            pen = QPen(Qt.red, 2 / self.scale_factor)
            self.path_item = self.scene.addPath(self.path, pen)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            if self.points:
                self.path.lineTo(self.points[0])
                pen = QPen(Qt.red, 2 / self.scale_factor)
                self.scene.removeItem(self.path_item)
                self.path_item = self.scene.addPath(self.path, pen)
        super().mouseReleaseEvent(event)

    def undo_last(self):
        if not self.points:
            return
        self.points.pop()
        self._redraw_path()

    def clear_annotation(self):
        self.points = []
        self.path = QPainterPath()
        if self.path_item:
            self.scene.removeItem(self.path_item)
            self.path_item = None

    def _redraw_path(self):
        self.path = QPainterPath()
        if self.points:
            self.path.moveTo(self.points[0])
            for pt in self.points[1:]:
                self.path.lineTo(pt)
            if not self.drawing:
                self.path.lineTo(self.points[0])
        if self.path_item:
            self.scene.removeItem(self.path_item)
        if not self.path.isEmpty():
            pen = QPen(Qt.red, 2 / self.scale_factor)
            self.path_item = self.scene.addPath(self.path, pen)

    def wheelEvent(self, event):
        # Zoom in/out with wheel
        zoom_in_factor = 1.25
        zoom_out_factor = 0.8
        if event.angleDelta().y() > 0:
            factor = zoom_in_factor
        else:
            factor = zoom_out_factor
        self.scale_factor *= factor
        self.scale(factor, factor)

    def export_mask(self, output_path):
        if not self.points:
            return False
        size = self.image.size()
        mask_img = QImage(size, QImage.Format_Grayscale8)
        mask_img.fill(0)
        painter = QPainter(mask_img)
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.white)
        painter.drawPath(self.path)
        painter.end()
        mask_img.save(output_path)
        return True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dataset Annotation Tool")
        self.dataset_dir = os.path.join(os.getcwd(), "datasets")
        os.makedirs(self.dataset_dir, exist_ok=True)

        self.canvas = AnnotationCanvas()

        load_btn = QPushButton("Load Image")
        load_btn.clicked.connect(self.load_image)
        save_btn = QPushButton("Save Annotation")
        save_btn.clicked.connect(self.save_annotation)
        undo_btn = QPushButton("Undo")
        undo_btn.clicked.connect(self.canvas.undo_last)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.canvas.clear_annotation)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(load_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(undo_btn)
        btn_layout.addWidget(clear_btn)

        self.list_widget = QListWidget()
        self.list_widget.setFixedHeight(100)
        self.update_dataset_list()

        layout = QVBoxLayout()
        layout.addLayout(btn_layout)
        layout.addWidget(self.canvas)
        layout.addWidget(self.list_widget)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.current_file = None

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.bmp)"
        )
        if file_path:
            self.current_file = file_path
            self.canvas.load_image(file_path)

    def save_annotation(self):
        if not self.current_file:
            QMessageBox.warning(self, "Warning", "No image loaded.")
            return
        name, ok = QInputDialog.getText(
            self, "Object Name", "Enter object label:"
        )
        if not ok or not name.strip():
            QMessageBox.warning(self, "Warning", "Invalid object name.")
            return
        ext = os.path.splitext(self.current_file)[1]
        new_image_name = f"{name}_image{ext}"
        new_image_path = os.path.join(self.dataset_dir, new_image_name)
        shutil.copy(self.current_file, new_image_path)
        mask_name = f"{name}_mask.png"
        mask_path = os.path.join(self.dataset_dir, mask_name)
        success = self.canvas.export_mask(mask_path)
        if success:
            QMessageBox.information(
                self, "Saved", f"Annotation saved:\n{new_image_name}\n{mask_name}"
            )
            self.update_dataset_list()
        else:
            QMessageBox.warning(self, "Warning", "No annotation drawn.")

    def update_dataset_list(self):
        self.list_widget.clear()
        items = os.listdir(self.dataset_dir)
        prefixes = set()
        for fname in items:
            if '_' in fname:
                prefixes.add(fname.split('_')[0])
        for p in sorted(prefixes):
            self.list_widget.addItem(p)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
