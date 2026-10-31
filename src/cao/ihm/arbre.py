"""Panneau de gauche : arbre du document, ou panneau de propriétés.

Les deux occupent la même place (cahier des charges §2.2) : quand on édite
une fonction, le panneau de propriétés remplace l'arbre, puis l'arbre revient.
Le contenu de départ de l'arbre dépend du type de document.
"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cao.fichiers.types_documents import TypeDocument
from cao.ihm import textes
from cao.ihm.icones import icone
from cao.ihm.panneaux.mesure import PanneauMesure

ICONE_DOCUMENT: dict[TypeDocument, str] = {
    TypeDocument.PIECE: "piece",
    TypeDocument.ASSEMBLAGE: "contrainte",
    TypeDocument.MISE_EN_PLAN: "vues",
}


class ArbreConstruction(QTreeWidget):
    """Pièce : plans + origine. Assemblage : idem + dossier Contraintes. Plan : feuilles.

    Le nom du document (racine) se modifie par double-clic ou F2.
    """

    nom_document_saisi = Signal(str)  # nouveau nom tapé par l'utilisateur

    def __init__(
        self, nom_document: str, type_document: TypeDocument, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("arbre")
        self.setHeaderHidden(True)
        self.setIconSize(QSize(18, 18))
        self.setIndentation(16)
        self.racine = QTreeWidgetItem(self, [nom_document])
        self.racine.setIcon(0, icone(ICONE_DOCUMENT[type_document]))
        self.racine.setFlags(self.racine.flags() | Qt.ItemFlag.ItemIsEditable)
        self.racine.setToolTip(0, textes.RENOMMER_ASTUCE)
        self.setEditTriggers(
            QTreeWidget.EditTrigger.DoubleClicked | QTreeWidget.EditTrigger.EditKeyPressed
        )
        self.itemChanged.connect(self._element_modifie)

        if type_document == TypeDocument.MISE_EN_PLAN:
            QTreeWidgetItem(self.racine, [textes.ARBRE_FEUILLE]).setIcon(0, icone("feuille"))
        else:
            for nom in textes.ARBRE_PLANS:
                QTreeWidgetItem(self.racine, [nom]).setIcon(0, icone("plan"))
            QTreeWidgetItem(self.racine, [textes.ARBRE_ORIGINE]).setIcon(0, icone("origine"))
            if type_document == TypeDocument.ASSEMBLAGE:
                dossier = QTreeWidgetItem(self.racine, [textes.ARBRE_CONTRAINTES])
                dossier.setIcon(0, icone("dossier"))
        self.expandAll()

    def _element_modifie(self, element: QTreeWidgetItem, _colonne: int) -> None:
        if element is self.racine:
            self.nom_document_saisi.emit(element.text(0))

    def afficher_nom_document(self, nom: str) -> None:
        """Met à jour le nom affiché, sans redéclencher `nom_document_saisi`."""
        if self.racine.text(0) != nom:
            self.blockSignals(True)
            self.racine.setText(0, nom)
            self.blockSignals(False)

    def noms_elements(self) -> list[str]:
        enfants = (self.racine.child(i) for i in range(self.racine.childCount()))
        return [enfant.text(0) for enfant in enfants if enfant is not None]


def _avec_titre(titre: str, contenu: QWidget) -> QWidget:
    """Encadre un contenu avec un petit titre en capitales."""
    cadre = QWidget()
    disposition = QVBoxLayout(cadre)
    disposition.setContentsMargins(0, 0, 0, 0)
    disposition.setSpacing(0)
    etiquette = QLabel(titre.upper())
    etiquette.setObjectName("titre_panneau")
    disposition.addWidget(etiquette)
    disposition.addWidget(contenu, stretch=1)
    return cadre


class PanneauProprietes(QWidget):
    """Paramètres de la fonction en cours d'édition (rempli à partir du lot 3)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(14, 4, 14, 14)
        vide = QLabel(textes.PANNEAU_VIDE)
        vide.setWordWrap(True)
        disposition.addWidget(vide)
        disposition.addStretch()


class PanneauGauche(QStackedWidget):
    """Empile l'arbre et le panneau de propriétés ; un seul est visible à la fois."""

    def __init__(
        self, nom_document: str, type_document: TypeDocument, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("panneau_gauche")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.arbre = ArbreConstruction(nom_document, type_document)
        self.proprietes = PanneauProprietes()
        self._page_arbre = _avec_titre(textes.ARBRE_TITRE[type_document], self.arbre)
        self._page_proprietes = _avec_titre(textes.PANNEAU_PROPRIETES, self.proprietes)
        self.mesure = PanneauMesure()
        self.mesure.fermer_demande.connect(self.montrer_arbre)
        self._page_mesure = _avec_titre(textes.MESURE_TITRE, self.mesure)
        self.addWidget(self._page_arbre)
        self.addWidget(self._page_proprietes)
        self.addWidget(self._page_mesure)
        self.setMinimumWidth(200)

    def montre_arbre(self) -> bool:
        return self.currentWidget() is self._page_arbre

    def montrer_arbre(self) -> None:
        self.setCurrentWidget(self._page_arbre)

    def montrer_proprietes(self) -> None:
        self.setCurrentWidget(self._page_proprietes)

    def montre_mesure(self) -> bool:
        return self.currentWidget() is self._page_mesure

    def montrer_mesure(self) -> None:
        self.setCurrentWidget(self._page_mesure)
