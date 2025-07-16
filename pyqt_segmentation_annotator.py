import sys
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QInputDialog, QMessageBox, QGraphicsView,
    QGraphicsScene
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
            pen = QPen(Qt.red, 2)
            self.path_item = self.scene.addPath(self.path, pen)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            # Close path
            if self.points:
                self.path.lineTo(self.points[0])
                pen = QPen(Qt.red, 2)
                self.scene.removeItem(self.path_item)
                self.path_item = self.scene.addPath(self.path, pen)
        super().mouseReleaseEvent(event)

    def export_mask(self, output_path):
        if not self.points:
            return False
        size = self.image.size()
        mask_img = QImage(size, QImage.Format_Grayscale8)
        mask_img.fill(0)
        painter = QPainter(mask_img)
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.white)
        # Convert QPainterPath to polygon for filling
        painter.drawPath(self.path)
        painter.end()
        mask_img.save(output_path)
        return True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dataset Annotation Tool")
        self.canvas = AnnotationCanvas()

        load_btn = QPushButton("Load Image")
        load_btn.clicked.connect(self.load_image)
        save_btn = QPushButton("Save Annotation")
        save_btn.clicked.connect(self.save_annotation)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(load_btn)
        btn_layout.addWidget(save_btn)

        layout = QVBoxLayout()
        layout.addLayout(btn_layout)
        layout.addWidget(self.canvas)

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
        base_dir = os.path.dirname(self.current_file)
        ext = os.path.splitext(self.current_file)[1]
        # Copy and rename image
        new_image_name = f"{name}_image{ext}"
        new_image_path = os.path.join(base_dir, new_image_name)
        shutil.copy(self.current_file, new_image_path)
        # Save mask
        mask_name = f"{name}_mask.png"
        mask_path = os.path.join(base_dir, mask_name)
        success = self.canvas.export_mask(mask_path)
        if success:
            QMessageBox.information(
                self, "Saved", f"Annotation saved:\n{new_image_name}\n{mask_name}"
            )
        else:
            QMessageBox.warning(self, "Warning", "No annotation drawn.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
