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

from collections.abc import Callable
from functools import partial
from typing import Protocol

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

from cao.document.document import Document, NomInvalide
from cao.fichiers.types_documents import INFOS, TypeDocument
from cao.ihm import textes
from cao.ihm.arbre import ICONE_DOCUMENT, PanneauGauche
from cao.ihm.feuille import FeuilleDessin
from cao.ihm.icones import icone
from cao.ihm.ruban import BarreAffichage, Ruban
from cao.ihm.theme import appliquer_theme
from cao.ihm.vue3d import Vue3D
from cao.noyau.affichage import FiltreSelection, ModeRendu, VueStandard
from cao.noyau.mesure import Forme, formater, mesurer

DUREE_MESSAGE_MS = 4000
HAUTEUR_PETIT_ECRAN = 800  # pixels utiles : en dessous, ruban sans grandes icônes


class CommandesVue(Protocol):
    """Ce que la fenêtre attend d'une vue 3D (permet de tester sans carte graphique)."""

    def orienter(self, vue_standard: VueStandard) -> None: ...
    def ajuster(self) -> None: ...
    def changer_mode_rendu(self, mode: ModeRendu) -> None: ...
    def changer_filtre(self, filtre: FiltreSelection) -> None: ...
    def vue_normale(self) -> bool: ...


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
        self.document = Document(type_document, nom_document or f"{info.nom_base}1")
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
            self.barre_affichage.outil_demande.connect(self.executer_commande)
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
        self.ruban.outil_demande.connect(self.executer_commande)
        self.commandes: dict[str, Callable[[], None]] = {}
        self.document.historique.abonner(self.rafraichir_document)
        self.panneau_gauche.arbre.nom_document_saisi.connect(self.renommer_document)
        self.rafraichir_document()
        self.selection: list[Forme] = []
        self.commandes["mesurer"] = self.ouvrir_mesure
        if isinstance(self.zone_graphique, Vue3D):
            self.brancher_commandes_vue(self.zone_graphique)
            self.zone_graphique.selection_changee.connect(self.selection_changee)
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
        self._creer_annuler_retablir()
        coin_gauche = QWidget(self.ruban)  # rattaché au ruban, sinon Python le détruit
        coin_gauche.setObjectName("coin_fichier")
        disposition_gauche = QHBoxLayout(coin_gauche)
        disposition_gauche.setContentsMargins(0, 0, 6, 0)
        disposition_gauche.setSpacing(0)
        disposition_gauche.addWidget(self.bouton_fichier)
        disposition_gauche.addWidget(self.bouton_annuler)
        disposition_gauche.addWidget(self.bouton_retablir)
        self.ruban.setCornerWidget(coin_gauche, Qt.Corner.TopLeftCorner)

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
            return Vue3D(self)
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
        # Mesure rapide de la sélection (IHM-12), cachée quand il n'y a rien à mesurer.
        self.pastille_mesure = QLabel()
        self.pastille_mesure.setObjectName("pastille_mesure")
        self.pastille_mesure.setVisible(False)
        barre.addPermanentWidget(self.pastille_mesure)
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

    def brancher_commandes_vue(self, vue: CommandesVue) -> None:
        """Relie les commandes de vue et de rendu (IHM-02, IHM-03) à la vue 3D."""
        for nom_vue in VueStandard:
            self.commandes[f"vue_{nom_vue.value}"] = partial(vue.orienter, nom_vue)
        for mode in ModeRendu:
            self.commandes[f"rendu_{mode.value}"] = partial(vue.changer_mode_rendu, mode)
        for filtre in FiltreSelection:
            self.commandes[f"filtre_{filtre.value}"] = partial(vue.changer_filtre, filtre)
        self.commandes["ajuster"] = vue.ajuster
        self.commandes["vue_normale"] = partial(self._vue_normale, vue)

    def _vue_normale(self, vue: CommandesVue) -> None:
        if not vue.vue_normale():
            self.statusBar().showMessage(textes.VUE_NORMALE_IMPOSSIBLE, DUREE_MESSAGE_MS)

    def ouvrir_mesure(self) -> None:
        """Évaluer > Mesurer : le panneau de mesure remplace l'arbre (IHM-12)."""
        self.panneau_gauche.montrer_mesure()
        self.selection_changee(self.selection)

    def selection_changee(self, formes: list[Forme]) -> None:
        """Nouvelle sélection : mesure rapide dans la barre d'état et le panneau de mesure."""
        self.selection = formes
        valeurs = mesurer(formes)
        self.pastille_mesure.setText("   ".join(formater(v) for v in valeurs))
        self.pastille_mesure.setVisible(bool(valeurs))
        self.panneau_gauche.mesure.afficher(valeurs, len(formes))

    def executer_commande(self, commande: str, nom_outil: str) -> None:
        """Exécute la commande d'un outil, ou annonce qu'elle n'est pas encore programmée."""
        action = self.commandes.get(commande)
        if action is None:
            self.annoncer_bientot(nom_outil)
        else:
            action()

    # --- Document : nom, annuler / rétablir (étape 1.5) ---

    @property
    def nom_document(self) -> str:
        return self.document.nom

    def _creer_annuler_retablir(self) -> None:
        """Boutons Annuler / Rétablir à côté de Fichier, raccourcis Ctrl+Z et Ctrl+Y."""
        self.action_annuler = QAction(icone("annuler"), textes.ANNULER, self)
        self.action_annuler.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_annuler.triggered.connect(self.annuler)
        self.action_retablir = QAction(icone("retablir"), textes.RETABLIR, self)
        # Ctrl+Y (Windows) et Ctrl+Maj+Z (Linux). Attention : ne jamais déclarer deux fois
        # la même touche sur une action, Qt la juge alors ambiguë et ne fait rien.
        self.action_retablir.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self.action_retablir.triggered.connect(self.retablir)
        self.addActions([self.action_annuler, self.action_retablir])
        self.bouton_annuler = QToolButton()
        self.bouton_annuler.setDefaultAction(self.action_annuler)
        self.bouton_retablir = QToolButton()
        self.bouton_retablir.setDefaultAction(self.action_retablir)
        for bouton in (self.bouton_annuler, self.bouton_retablir):
            bouton.setObjectName("bouton_historique")
            bouton.setAutoRaise(True)

    def annuler(self) -> None:
        self._sans_erreur(self.document.historique.annuler)

    def retablir(self) -> None:
        self._sans_erreur(self.document.historique.retablir)

    def _sans_erreur(self, action: Callable[[], object]) -> None:
        """Un échec ne doit jamais bloquer l'interface (§8.4) : on l'affiche et on continue."""
        try:
            action()
        except Exception as erreur:
            self.statusBar().showMessage(str(erreur), DUREE_MESSAGE_MS)

    def renommer_document(self, nom: str) -> None:
        try:
            self.document.renommer(nom)
        except NomInvalide as erreur:
            self.statusBar().showMessage(str(erreur), DUREE_MESSAGE_MS)
        self.rafraichir_document()  # remet l'ancien nom dans l'arbre en cas de refus

    def rafraichir_document(self) -> None:
        """Met l'interface à jour après une modification du document."""
        historique = self.document.historique
        self.setWindowTitle(
            textes.titre_fenetre(self.document.nom, INFOS[self.type_document].libelle)
        )
        self.setWindowModified(self.document.modifie)
        self.panneau_gauche.arbre.afficher_nom_document(self.document.nom)
        self.action_annuler.setEnabled(historique.peut_annuler)
        self.action_retablir.setEnabled(historique.peut_retablir)
        self.action_annuler.setToolTip(
            textes.info_annuler(historique.libelle_annuler) + "  (Ctrl+Z)"
        )
        self.action_retablir.setToolTip(
            textes.info_retablir(historique.libelle_retablir) + "  (Ctrl+Y)"
        )

    def annoncer_bientot(self, nom_outil: str) -> None:
        """Message temporaire pour un outil pas encore programmé."""
        self.statusBar().showMessage(textes.message_bientot(nom_outil), DUREE_MESSAGE_MS)
