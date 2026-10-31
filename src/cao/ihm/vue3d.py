"""Zone graphique 3D : visualiseur OpenCascade intégré à Qt (IHM-01 à IHM-03).

Souris, comme SolidWorks :
    clic molette + glisser        -> rotation
    Ctrl + clic molette + glisser -> panoramique
    molette                       -> zoom centré sur le curseur
    clic gauche sur le cube       -> vue correspondante (face, arête ou coin)
Clavier :
    flèches -> rotation de 15° (utile sur un pavé tactile sans molette)
    F       -> ajuster la vue au modèle

Les calculs de vue sont faits par cao.noyau.affichage ; ce module ne gère
que les événements Qt.
"""

from typing import Any, Protocol

from OCC.Display.backend import load_backend

load_backend("pyside6")  # doit précéder l'import de qtDisplay

from OCC.Display import qtDisplay  # noqa: E402
from PySide6.QtCore import QPointF, Qt, Signal  # noqa: E402
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPaintEvent, QWheelEvent  # noqa: E402

from cao.noyau import affichage as noyau_affichage  # noqa: E402
from cao.noyau.affichage import FiltreSelection, ModeRendu, VueStandard  # noqa: E402
from cao.noyau.mesure import premiere_normale_plane  # noqa: E402

COULEUR_FOND_HAUT = (235, 240, 248)
COULEUR_FOND_BAS = (170, 185, 210)
FACTEUR_ZOOM = 1.2
SEUIL_CLIC_PX = 4  # en dessous de ce déplacement, un appui-relâché est un clic


class Intercepteur(Protocol):
    """Mode qui reçoit la souris et le clavier avant la vue (positions en pixels réels)."""

    def clic_ecran(self, x: int, y: int) -> bool: ...
    def mouvement_ecran(self, x: int, y: int) -> None: ...
    def terminer_trace(self) -> None: ...
    def double_clic_ecran(self, x: int, y: int) -> None: ...
    def touche(self, cle: int) -> bool: ...


class Vue3D(qtDisplay.qtViewer3d):
    """Visualiseur 3D avec la navigation façon SolidWorks."""

    # Attributs créés par pythonocc (déclarés ici pour la vérification des types).
    dragStartPosX: int
    dragStartPosY: int
    _inited: bool

    _libere = False

    # Émis à chaque changement de sélection, avec la liste des formes sélectionnées.
    selection_changee = Signal(list)
    initialisee = Signal()  # la vue OpenGL est prête : on peut afficher
    # Mode qui intercepte la souris et le clavier (le mode esquisse), ou None.
    intercepteur: "Intercepteur | None" = None

    def InitDriver(self) -> None:
        """Crée le contexte OpenGL puis applique l'apparence du logiciel."""
        if self._libere:
            return
        super().InitDriver()
        affichage: Any = self._display
        affichage.set_bg_gradient_color(list(COULEUR_FOND_HAUT), list(COULEUR_FOND_BAS))
        noyau_affichage.configurer_apparence(affichage.Context)
        noyau_affichage.configurer_eclairage(affichage.Viewer)
        self.cube = noyau_affichage.creer_cube_de_vue()
        affichage.Context.Display(self.cube, False)
        self.mode_rendu = ModeRendu.OMBRE_ARETES
        self.filtre = FiltreSelection.TOUT
        noyau_affichage.appliquer_mode_rendu(affichage.Context, affichage.View, self.mode_rendu)
        noyau_affichage.orienter(affichage.View, VueStandard.ISOMETRIQUE)
        noyau_affichage.centrer_sur_origine(affichage.View)  # scène vide : cadrage raisonnable
        # Touches de pythonocc remplacées par celles du logiciel.
        self._key_map = {ord("F"): self.ajuster}
        self.initialisee.emit()

    # --- Commandes appelées par la barre d'affichage et le ruban ---

    @property
    def prete(self) -> bool:
        return bool(self._inited) and not self._libere

    @property
    def contexte(self) -> Any:
        """Contexte d'affichage d'OpenCascade (AIS_InteractiveContext)."""
        return self._display.Context

    @property
    def vue_occ(self) -> Any:
        """Vue d'OpenCascade (V3d_View)."""
        return self._display.View

    def orienter(self, vue_standard: VueStandard) -> None:
        if self.prete:
            noyau_affichage.orienter(self._display.View, vue_standard)

    def ajuster(self) -> None:
        if self.prete:
            self._display.View.FitAll(0.1, True)
            self._display.View.Redraw()

    def changer_filtre(self, filtre: FiltreSelection) -> None:
        if self.prete:
            self.filtre = filtre
            noyau_affichage.appliquer_filtre(self._display.Context, filtre)
            self.selection_changee.emit([])

    def vue_normale(self) -> bool:
        """Regarde de face la première face plane sélectionnée ; False s'il n'y en a pas."""
        if not self.prete:
            return False
        formes = noyau_affichage.formes_selectionnees(self._display.Context)
        normale = premiere_normale_plane(formes)
        if normale is None:
            return False
        noyau_affichage.orienter_normale(self._display.View, normale)
        return True

    def changer_mode_rendu(self, mode: ModeRendu) -> None:
        if self.prete:
            self.mode_rendu = mode
            noyau_affichage.appliquer_mode_rendu(self._display.Context, self._display.View, mode)

    # --- Fermeture ---

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

    # --- Événements Qt ---

    def paintEvent(self, event: QPaintEvent) -> None:
        if self._libere:
            return  # vue libérée : plus rien à dessiner
        super().paintEvent(event)

    # La souris est gérée entièrement ici. Qt donne des positions en pixels
    # « logiques » ; OpenCascade attend des pixels réels de l'écran. Sur un écran
    # agrandi par Windows (125 %, 150 %…), il faut multiplier par ce facteur,
    # sinon les clics tombent à côté de ce qui est visé.

    def _pixels(self, point: QPointF) -> tuple[int, int]:
        """Position Qt -> pixels réels d'OpenCascade."""
        facteur = self.devicePixelRatioF()
        return round(point.x() * facteur), round(point.y() * facteur)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        self.dragStartPosX, self.dragStartPosY = self._pixels(event.position())
        if self.prete and event.button() == Qt.MouseButton.MiddleButton:
            self._display.StartRotation(self.dragStartPosX, self.dragStartPosY)

    def mouseMoveEvent(self, evt: QMouseEvent) -> None:
        if not self.prete:
            return
        x, y = self._pixels(evt.position())
        if evt.buttons() == Qt.MouseButton.MiddleButton:
            if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._display.Pan(x - self.dragStartPosX, self.dragStartPosY - y)
                self.dragStartPosX, self.dragStartPosY = x, y
            else:
                # La rotation a été démarrée à l'appui (StartRotation).
                self._display.Rotation(x, y)
        elif evt.buttons() == Qt.MouseButton.NoButton:
            self._display.MoveTo(x, y)  # surbrillance de ce qui est sous la souris (IHM-04)
            if self.intercepteur is not None:
                self.intercepteur.mouvement_ecran(x, y)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self.intercepteur is not None and event.button() == Qt.MouseButton.LeftButton:
            x, y = self._pixels(event.position())
            self.intercepteur.double_clic_ecran(x, y)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if not self.prete:
            return
        if event.button() == Qt.MouseButton.RightButton and self.intercepteur is not None:
            self.intercepteur.terminer_trace()  # clic droit : fin d'une suite de lignes
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        x, y = self._pixels(event.position())
        deplacement = abs(x - self.dragStartPosX) + abs(y - self.dragStartPosY)
        if deplacement > SEUIL_CLIC_PX * self.devicePixelRatioF():
            return  # glisser au bouton gauche : réservé à la sélection par rectangle (plus tard)
        contexte = self._display.Context
        if noyau_affichage.clic_sur_cube(contexte, self._display.View, x, y):
            return
        if self.intercepteur is not None and self.intercepteur.clic_ecran(x, y):
            return  # le clic a servi au tracé
        # Ctrl + clic ajoute ou retire une entité de la sélection, comme SolidWorks.
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._display.ShiftSelect(x, y)
        else:
            self._display.Select(x, y)
        self.selection_changee.emit(noyau_affichage.formes_selectionnees(contexte))

    def wheelEvent(self, event: QWheelEvent) -> None:
        if not self.prete:
            return
        x, y = self._pixels(event.position())
        facteur = FACTEUR_ZOOM if event.angleDelta().y() > 0 else 1 / FACTEUR_ZOOM
        noyau_affichage.zoomer_au_point(self._display.View, x, y, facteur)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        pas = noyau_affichage.PAS_ROTATION_CLAVIER
        rotations = {
            Qt.Key.Key_Left: (-pas, 0.0),
            Qt.Key.Key_Right: (pas, 0.0),
            Qt.Key.Key_Up: (0.0, -pas),
            Qt.Key.Key_Down: (0.0, pas),
        }
        cle = Qt.Key(event.key())
        if self.intercepteur is not None and self.intercepteur.touche(cle):
            return
        if cle in rotations and self.prete:
            horizontal, vertical = rotations[cle]
            noyau_affichage.tourner(self._display.View, horizontal, vertical)
            return
        super().keyPressEvent(event)
