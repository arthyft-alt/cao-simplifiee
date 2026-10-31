"""Prototype 0.2 — afficher une boîte OpenCascade dans une fenêtre PySide6.

Script jetable : il sert seulement à vérifier que l'affichage 3D marche
sur ce poste avant de construire le vrai logiciel.

Lancement (dans le terminal VS Code, environnement cao actif) :
    python prototypes/affichage.py

Souris (comme SolidWorks) :
    clic molette maintenu + glisser        -> rotation
    Ctrl + clic molette maintenu + glisser -> panoramique (déplacer la vue)
    molette                                -> zoom
Clavier : F = ajuster la vue, W = filaire, S = ombré, H = lignes cachées.

Option --test : la fenêtre se ferme seule après 3 secondes (vérification automatique).
"""

import sys

from OCC.Display.backend import load_backend

load_backend("pyside6")  # doit être appelé avant d'importer qtDisplay

from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Display import qtDisplay
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow


class Vue3D(qtDisplay.qtViewer3d):
    """Vue 3D de pythonocc, avec la navigation à la molette façon SolidWorks."""

    def mouseMoveEvent(self, evt):
        if evt.buttons() == Qt.MouseButton.MiddleButton:
            point = evt.pos()
            ctrl = bool(evt.modifiers() & Qt.KeyboardModifier.ControlModifier)
            if ctrl:
                # Panoramique : on décale la vue du déplacement de la souris.
                dx = point.x() - self.dragStartPosX
                dy = point.y() - self.dragStartPosY
                self.dragStartPosX = point.x()
                self.dragStartPosY = point.y()
                self._display.Pan(dx, -dy)
            else:
                # Rotation : la rotation a été démarrée au clic (mousePressEvent).
                self._display.Rotation(point.x(), point.y())
            return
        super().mouseMoveEvent(evt)

    def wheelEvent(self, event):
        # Zoom plus doux que celui d'origine (x2 à chaque cran).
        facteur = 1.25 if event.angleDelta().y() > 0 else 0.8
        self._display.ZoomFactor(facteur)


class Fenetre(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prototype 0.2 — boîte 100 × 50 × 20 mm")
        self.resize(1024, 768)
        self.vue = Vue3D(self)
        self.setCentralWidget(self.vue)


def main():
    app = QApplication(sys.argv)
    fenetre = Fenetre()
    fenetre.show()
    fenetre.vue.InitDriver()  # crée le contexte OpenGL dans la fenêtre

    affichage = fenetre.vue._display
    affichage.set_bg_gradient_color([235, 240, 248], [170, 185, 210])
    affichage.display_triedron()

    boite = BRepPrimAPI_MakeBox(100.0, 50.0, 20.0).Shape()  # longueurs en mm
    affichage.DisplayShape(boite, color="ORANGE", update=True)
    affichage.View_Iso()
    affichage.FitAll()

    if "--test" in sys.argv:
        QTimer.singleShot(3000, app.quit)
        print("Affichage 3D lancé sans erreur.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
