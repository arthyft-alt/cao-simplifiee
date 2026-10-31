"""Ruban à onglets (haut de la fenêtre) et barre d'affichage (haut de la zone 3D).

Ruban « simplifié » sur une seule ligne, pour laisser le maximum de place à la
zone de travail. Le bouton Fichier et la recherche sont posés sur la ligne des
onglets (coins du ruban). Il s'adapte à la largeur disponible :
    « grand »   : icône et nom côte à côte ;
    « moyen »   : icône plus petite et nom côte à côte ;
    « compact » : icônes seules (le nom reste visible dans l'info-bulle).
Il choisit la plus grande présentation qui tient sans déborder.
"""

from dataclasses import dataclass

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QTabWidget,
    QToolBar,
    QToolButton,
    QWidget,
)

from cao.ihm import textes
from cao.ihm.icones import icone


@dataclass(frozen=True)
class ModeRuban:
    nom: str
    taille_icone: int
    style: Qt.ToolButtonStyle


MODES: list[ModeRuban] = [
    ModeRuban("grand", 22, Qt.ToolButtonStyle.ToolButtonTextBesideIcon),
    ModeRuban("moyen", 18, Qt.ToolButtonStyle.ToolButtonTextBesideIcon),
    ModeRuban("compact", 22, Qt.ToolButtonStyle.ToolButtonIconOnly),
]


def choisir_mode(largeurs: list[tuple[str, int]], disponible: int) -> str:
    """Premier mode (du plus grand au plus petit) dont la largeur tient ; sinon le dernier."""
    for nom, largeur in largeurs:
        if largeur <= disponible:
            return nom
    return largeurs[-1][0]


def _info_bulle(outil: textes.Outil) -> str:
    return f"<b>{outil.nom}</b><br>{outil.info}"


class GroupeRuban(QWidget):
    """Boutons d'une même famille (ex. « Tracer »), côte à côte."""

    def __init__(self, groupe: textes.Groupe, ruban: "Ruban") -> None:
        super().__init__()
        self.nom = groupe.nom
        self.boutons: list[QToolButton] = []
        ligne = QHBoxLayout(self)
        ligne.setContentsMargins(0, 0, 0, 0)
        ligne.setSpacing(1)
        for outil in groupe.outils:
            action = QAction(icone(outil.icone), outil.nom, self)
            action.setToolTip(_info_bulle(outil))
            action.triggered.connect(lambda _=False, n=outil.nom: ruban.outil_demande.emit(n))
            bouton = QToolButton()
            bouton.setDefaultAction(action)
            bouton.setAutoRaise(True)
            bouton.setProperty("nom_outil", outil.nom)
            self.boutons.append(bouton)
            ligne.addWidget(bouton)

    def appliquer_mode(self, mode: ModeRuban) -> None:
        for bouton in self.boutons:
            bouton.setToolButtonStyle(mode.style)
            bouton.setIconSize(QSize(mode.taille_icone, mode.taille_icone))
            bouton.updateGeometry()  # la taille du bouton change avec la présentation
        disposition = self.layout()
        if disposition is not None:
            disposition.invalidate()
            disposition.activate()


class PageRuban(QWidget):
    """Contenu d'un onglet : les groupes séparés par un trait vertical."""

    def __init__(self, groupes: list[textes.Groupe], ruban: "Ruban") -> None:
        super().__init__()
        self.setObjectName("page_ruban")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        disposition = QHBoxLayout(self)
        disposition.setContentsMargins(6, 3, 6, 3)
        disposition.setSpacing(2)
        self.groupes: list[GroupeRuban] = []
        for i, groupe in enumerate(groupes):
            if i > 0:
                trait = QFrame()
                trait.setObjectName("separateur_groupe")
                trait.setFixedWidth(1)
                disposition.addWidget(trait)
            widget = GroupeRuban(groupe, ruban)
            self.groupes.append(widget)
            disposition.addWidget(widget)
        disposition.addStretch()

    def appliquer_mode(self, mode: ModeRuban) -> None:
        for groupe in self.groupes:
            groupe.appliquer_mode(mode)
        disposition = self.layout()
        if disposition is not None:
            disposition.invalidate()
            disposition.activate()

    def largeur_necessaire(self) -> int:
        return sum(g.sizeHint().width() for g in self.groupes) + 12 + 14 * len(self.groupes)


class Ruban(QTabWidget):
    """Onglets propres au type de document ; s'adapte à la largeur de la fenêtre."""

    outil_demande = Signal(str)  # émis avec le nom de l'outil cliqué

    def __init__(self, onglets: list[textes.Onglet], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ruban")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)  # fond blanc derrière les coins
        self.setDocumentMode(True)
        self.tabBar().setDrawBase(False)  # pas de trait gris sous les onglets
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.pages: list[PageRuban] = []
        for onglet in onglets:
            page = PageRuban(onglet.groupes, self)
            self.pages.append(page)
            self.addTab(page, onglet.nom)
        self.modes_autorises = list(MODES)
        self.mode = MODES[0]
        self.currentChanged.connect(lambda _index: self.adapter(self.width()))
        self.adapter(1280)

    def regler_pour_petit_ecran(self, petit: bool) -> None:
        """Sur un écran peu haut ou étroit, on commence directement aux icônes moyennes."""
        self.modes_autorises = [m for m in MODES if not (petit and m.nom == "grand")]
        self.adapter(self.width())

    def noms_onglets(self) -> list[str]:
        return [self.tabText(i) for i in range(self.count())]

    def hauteur_ligne_onglets(self) -> int:
        """Hauteur de la ligne des onglets, coins (Fichier, recherche) compris."""
        hauteurs = [self.tabBar().sizeHint().height()]
        for coin in (Qt.Corner.TopLeftCorner, Qt.Corner.TopRightCorner):
            widget = self.cornerWidget(coin)
            if widget is not None:
                hauteurs.append(widget.sizeHint().height())
        return max(hauteurs)

    def adapter(self, largeur_disponible: int) -> str:
        """Choisit la présentation qui tient dans la largeur ; renvoie son nom."""
        page = self.pages[self.currentIndex()]
        largeurs = []
        for mode in self.modes_autorises:
            page.appliquer_mode(mode)
            largeurs.append((mode.nom, page.largeur_necessaire()))
        nom = choisir_mode(largeurs, largeur_disponible)
        self.mode = next(m for m in self.modes_autorises if m.nom == nom)
        for p in self.pages:
            p.appliquer_mode(self.mode)
        self.setFixedHeight(self.hauteur_ligne_onglets() + page.sizeHint().height())
        return nom

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if event.size().width() != event.oldSize().width():
            self.adapter(event.size().width())


class BarreAffichage(QToolBar):
    """Vues standard, en icônes seules, au-dessus de la zone 3D."""

    outil_demande = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("barre_affichage")
        self.setMovable(False)
        self.setIconSize(QSize(18, 18))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        espace_gauche = QWidget()
        espace_gauche.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(espace_gauche)
        for outil in textes.BARRE_AFFICHAGE:
            action = QAction(icone(outil.icone), outil.nom, self)
            action.setToolTip(_info_bulle(outil))
            action.triggered.connect(lambda _=False, n=outil.nom: self.outil_demande.emit(n))
            self.addAction(action)
        espace_droite = QWidget()
        espace_droite.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(espace_droite)

    def actions_vues(self) -> list[QAction]:
        """Les actions de vue, sans les espaces de centrage."""
        return [a for a in self.actions() if a.text()]
