"""Zone graphique 3D : visualiseur OpenCascade intégré à Qt.

Navigation à la souris façon SolidWorks (exigence IHM-01, finalisée à l'étape 1.3) :
    clic molette + glisser        -> rotation
    Ctrl + clic molette + glisser -> panoramique
    molette                       -> zoom
"""

from typing import Any

from OCC.Display.backend import load_backend

load_backend("pyside6")  # doit précéder l'import de qtDisplay

from OCC.Display import qtDisplay  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent, QPaintEvent, QWheelEvent  # noqa: E402

COULEUR_FOND_HAUT = (235, 240, 248)
COULEUR_FOND_BAS = (170, 185, 210)
FACTEUR_ZOOM = 1.25


class Vue3D(qtDisplay.qtViewer3d):
    """Visualiseur 3D avec la navigation à la molette."""

    # Position de la souris au début du glissement (attributs créés par pythonocc).
    dragStartPosX: int
    dragStartPosY: int
    _inited: bool

    _libere = False

    def InitDriver(self) -> None:
        """Crée le contexte OpenGL puis applique l'apparence du logiciel."""
        if self._libere:
            return
        super().InitDriver()
        affichage: Any = self._display
        affichage.set_bg_gradient_color(list(COULEUR_FOND_HAUT), list(COULEUR_FOND_BAS))
        affichage.display_triedron()
        affichage.View_Iso()

    def liberer(self) -> None:
        """Libère la vue OpenGL tant que la fenêtre existe encore.

        À appeler à la fermeture de la fenêtre. Sans cela, OpenCascade détruit
        sa vue plus tard, quand la fenêtre Windows a déjà disparu, et affiche
        l'erreur « wglMakeCurrent() has failed. Descripteur non valide ».
        """
        if self._libere:
            return
        self._libere = True
        if self._inited:
            affichage: Any = self._display
            affichage.Context.RemoveAll(False)
            affichage.View.Remove()
            self._inited = False

    def paintEvent(self, event: QPaintEvent) -> None:
        if self._libere:
            return  # vue libérée : plus rien à dessiner
        super().paintEvent(event)

    def mouseMoveEvent(self, evt: QMouseEvent) -> None:
        if evt.buttons() == Qt.MouseButton.MiddleButton:
            point = evt.position().toPoint()
            ctrl = bool(evt.modifiers() & Qt.KeyboardModifier.ControlModifier)
            if ctrl:
                dx = point.x() - self.dragStartPosX
                dy = point.y() - self.dragStartPosY
                self.dragStartPosX = point.x()
                self.dragStartPosY = point.y()
                self._display.Pan(dx, -dy)
            else:
                # La rotation a été démarrée au clic (mousePressEvent de pythonocc).
                self._display.Rotation(point.x(), point.y())
            return
        super().mouseMoveEvent(evt)

    def wheelEvent(self, event: QWheelEvent) -> None:
        facteur = FACTEUR_ZOOM if event.angleDelta().y() > 0 else 1 / FACTEUR_ZOOM
        self._display.ZoomFactor(facteur)
