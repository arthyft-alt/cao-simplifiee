"""Fenêtre d'un document (cahier des charges §2.2 et DOC-01).

Chaque document (pièce, assemblage, mise en plan) s'ouvre dans sa propre
fenêtre, avec l'interface propre à son type, comme dans SolidWorks :
    - pièce        : ruban Esquisse / Fonctions / Évaluer / Affichage, vue 3D ;
    - assemblage   : ruban Assemblage / Évaluer / Affichage, vue 3D ;
    - mise en plan : ruban Disposition des vues / Annotation / Esquisse, feuille 2D.

Disposition :
    ┌──────────────────────────────────────────────┐
    │ [Fichier] Onglets du ruban      [Recherche]  │
    │ Outils de l'onglet, sur une seule ligne      │
    ├────────────┬─────────────────────────────────┤
    │ Arbre ou   │ Barre d'affichage (3D seulement) │
    │ propriétés │ Vue 3D ou feuille de dessin      │
    ├────────────┴─────────────────────────────────┤
    │ Astuce                        pastilles d'état│
    └──────────────────────────────────────────────┘
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from cao.fichiers.types_documents import INFOS, TypeDocument
from cao.ihm import textes
from cao.ihm.arbre import ICONE_DOCUMENT, PanneauGauche
from cao.ihm.feuille import FeuilleDessin
from cao.ihm.icones import icone
from cao.ihm.ruban import BarreAffichage, Ruban
from cao.ihm.theme import appliquer_theme

DUREE_MESSAGE_MS = 4000
HAUTEUR_PETIT_ECRAN = 800  # pixels utiles : en dessous, ruban sans grandes icônes


def hauteur_ecran_disponible() -> int:
    ecran = QGuiApplication.primaryScreen()
    return ecran.availableGeometry().height() if ecran else 900


class FenetreDocument(QMainWindow):
    """Fenêtre d'un document.

    avec_vue3d=False remplace la vue 3D par une zone vide : utile pour les tests
    automatiques, qui tournent sans carte graphique.
    """

    nouveau_demande = Signal()  # Fichier > Nouveau : le gestionnaire ouvre le choix du type
    quitter_demande = Signal()  # Fichier > Quitter : fermer toutes les fenêtres

    def __init__(
        self,
        type_document: TypeDocument = TypeDocument.PIECE,
        nom_document: str | None = None,
        avec_vue3d: bool = True,
    ) -> None:
        super().__init__()
        application = QApplication.instance()
        if isinstance(application, QApplication):
            appliquer_theme(application, hauteur_ecran_disponible())

        self.type_document = type_document
        info = INFOS[type_document]
        self.nom_document = nom_document or f"{info.nom_base}1"
        self.setWindowTitle(textes.titre_fenetre(self.nom_document, info.libelle))
        self.setWindowIcon(icone(ICONE_DOCUMENT[type_document]))
        self.setMinimumSize(900, 600)  # tient sur un écran 1366 × 768 (TEC-14)

        self.ruban = Ruban(textes.ONGLETS_PAR_TYPE[type_document])
        self.ruban.regler_pour_petit_ecran(hauteur_ecran_disponible() < HAUTEUR_PETIT_ECRAN)
        self._creer_menu()
        self.panneau_gauche = PanneauGauche(self.nom_document, type_document)
        self.zone_graphique = self._creer_zone_graphique(avec_vue3d and info.vue_3d)

        droite = QWidget()
        disposition_droite = QVBoxLayout(droite)
        disposition_droite.setContentsMargins(0, 0, 0, 0)
        disposition_droite.setSpacing(0)
        self.barre_affichage: BarreAffichage | None = None
        if info.vue_3d:  # pas de vues 3D standard sur une feuille de dessin
            self.barre_affichage = BarreAffichage()
            self.barre_affichage.outil_demande.connect(self.annoncer_bientot)
            disposition_droite.addWidget(self.barre_affichage)
        disposition_droite.addWidget(self.zone_graphique, stretch=1)

        self.separateur = QSplitter(Qt.Orientation.Horizontal)
        self.separateur.setChildrenCollapsible(False)
        self.separateur.addWidget(self.panneau_gauche)
        self.separateur.addWidget(droite)
        self.separateur.setStretchFactor(1, 1)

        centre = QWidget()
        disposition = QVBoxLayout(centre)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(0)
        disposition.addWidget(self.ruban)
        disposition.addWidget(self.separateur, stretch=1)
        self.setCentralWidget(centre)

        self._creer_barre_etat()
        self.ruban.outil_demande.connect(self.annoncer_bientot)
        self._dimensionner_selon_ecran()

    def _dimensionner_selon_ecran(self) -> None:
        """Ouvre la fenêtre à 85 % de l'écran, arbre à environ 20 % de la largeur."""
        ecran = QGuiApplication.primaryScreen()
        if ecran is None:
            self.resize(1280, 800)
        else:
            zone = ecran.availableGeometry()
            self.resize(int(zone.width() * 0.85), int(zone.height() * 0.85))
        largeur_arbre = max(220, min(320, self.width() // 5))
        self.separateur.setSizes([largeur_arbre, self.width() - largeur_arbre])

    def _creer_menu(self) -> None:
        """Menu Fichier et recherche, posés sur la ligne des onglets du ruban.

        Pas de barre de menus séparée : on gagne une ligne entière en hauteur.
        Les actions sont aussi ajoutées à la fenêtre pour que les raccourcis
        clavier (Ctrl+N, Ctrl+W, Ctrl+Q…) marchent même menu fermé.
        """
        self.menu_fichier = QMenu(textes.MENU_FICHIER, self)

        self.action_nouveau = QAction(icone("piece"), textes.ACTION_NOUVEAU, self)
        self.action_nouveau.setShortcut(QKeySequence.StandardKey.New)
        self.action_nouveau.triggered.connect(self.nouveau_demande.emit)
        self.menu_fichier.addAction(self.action_nouveau)

        for nom, raccourci in [
            (textes.ACTION_OUVRIR, QKeySequence.StandardKey.Open),
            (textes.ACTION_ENREGISTRER, QKeySequence.StandardKey.Save),
            (textes.ACTION_ENREGISTRER_SOUS, QKeySequence.StandardKey.SaveAs),
        ]:
            action = QAction(nom, self)
            action.setShortcut(raccourci)
            action.setEnabled(False)  # gestion des fichiers : étape 1.6
            self.menu_fichier.addAction(action)
        self.menu_fichier.addSeparator()

        self.action_fermer = QAction(textes.ACTION_FERMER, self)
        self.action_fermer.setShortcut(QKeySequence.StandardKey.Close)
        self.action_fermer.triggered.connect(self.close)
        self.menu_fichier.addAction(self.action_fermer)

        self.action_quitter = QAction(textes.ACTION_QUITTER, self)
        self.action_quitter.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_quitter.triggered.connect(self.quitter_demande.emit)
        self.menu_fichier.addAction(self.action_quitter)
        self.addActions(self.menu_fichier.actions())

        self.bouton_fichier = QToolButton()
        self.bouton_fichier.setObjectName("bouton_fichier")
        self.bouton_fichier.setText(textes.MENU_FICHIER.replace("&", ""))
        self.bouton_fichier.setMenu(self.menu_fichier)
        self.bouton_fichier.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.ruban.setCornerWidget(self.bouton_fichier, Qt.Corner.TopLeftCorner)

        # Recherche de commande (IHM-06, priorité P2) : emplacement réservé.
        self.recherche = QLineEdit()
        self.recherche.setObjectName("recherche")
        self.recherche.setPlaceholderText(textes.RECHERCHE_COMMANDE)
        self.recherche.addAction(icone("recherche"), QLineEdit.ActionPosition.LeadingPosition)
        self.recherche.setToolTip(textes.BIENTOT)
        self.recherche.setEnabled(False)
        self.recherche.setFixedWidth(220)
        # Conteneur avec marge à droite, rattaché au ruban (sinon Python le détruit).
        self.coin_recherche = QWidget(self.ruban)
        self.coin_recherche.setObjectName("coin_recherche")
        disposition_coin = QHBoxLayout(self.coin_recherche)
        disposition_coin.setContentsMargins(0, 2, 8, 2)
        disposition_coin.addWidget(self.recherche)
        self.ruban.setCornerWidget(self.coin_recherche, Qt.Corner.TopRightCorner)
        self.ruban.adapter(self.ruban.width())  # la ligne des onglets a changé de hauteur

    def _creer_zone_graphique(self, vue_3d: bool) -> QWidget:
        if self.type_document == TypeDocument.MISE_EN_PLAN:
            return FeuilleDessin()
        if vue_3d:
            from cao.ihm.vue3d import Vue3D  # import ici : nécessite une carte graphique

            vue: QWidget = Vue3D(self)
            return vue
        zone = QWidget()
        zone.setObjectName("zone_graphique_vide")
        return zone

    def closeEvent(self, event: QCloseEvent) -> None:
        # La vue 3D doit libérer OpenGL avant que la fenêtre Windows disparaisse.
        liberer = getattr(self.zone_graphique, "liberer", None)
        if callable(liberer):
            liberer()
        super().closeEvent(event)

    def _creer_barre_etat(self) -> None:
        self.pastilles: list[QLabel] = []
        barre = self.statusBar()
        barre.setSizeGripEnabled(False)
        for texte in textes.ETAT_PAR_TYPE[self.type_document]:
            pastille = QLabel(texte)
            pastille.setObjectName("pastille")
            self.pastilles.append(pastille)
            barre.addPermanentWidget(pastille)
        self.astuce = textes.ASTUCE_PAR_TYPE[self.type_document]
        barre.showMessage(self.astuce)
        # Quand un message temporaire s'efface, l'astuce revient.
        barre.messageChanged.connect(self._remettre_astuce)

    def _remettre_astuce(self, message: str) -> None:
        if not message:
            self.statusBar().showMessage(self.astuce)

    def annoncer_bientot(self, nom_outil: str) -> None:
        """Message temporaire pour un outil pas encore programmé."""
        self.statusBar().showMessage(textes.message_bientot(nom_outil), DUREE_MESSAGE_MS)
