"""Gestionnaire des documents ouverts : une fenêtre par document.

Il ouvre la fenêtre « Nouveau document », crée la fenêtre du type choisi,
numérote les documents (Pièce1, Pièce2, Assemblage1…) et garde la liste des
fenêtres ouvertes. C'est aussi lui qui, plus tard, fera communiquer les
documents entre eux (un assemblage mis à jour quand une pièce change, DOC-04).
"""

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QApplication, QWidget

from cao.fichiers.types_documents import CompteurDocuments, TypeDocument
from cao.ihm.fenetre import FenetreDocument, hauteur_ecran_disponible
from cao.ihm.nouveau_document import DialogueNouveauDocument
from cao.ihm.theme import appliquer_theme

DECALAGE_FENETRES_PX = 32  # chaque nouvelle fenêtre est décalée, pour les voir toutes


class GestionnaireDocuments(QObject):
    def __init__(self, avec_vue3d: bool = True) -> None:
        super().__init__()
        application = QApplication.instance()
        if isinstance(application, QApplication):
            appliquer_theme(application, hauteur_ecran_disponible())
        self.avec_vue3d = avec_vue3d
        self.compteur = CompteurDocuments()
        self.fenetres: list[FenetreDocument] = []

    def ouvrir(self, type_document: TypeDocument) -> FenetreDocument:
        """Crée un nouveau document du type donné, dans sa propre fenêtre."""
        fenetre = FenetreDocument(
            type_document, self.compteur.nom_suivant(type_document), self.avec_vue3d
        )
        fenetre.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        fenetre.nouveau_demande.connect(lambda: self.demander_nouveau(fenetre))
        fenetre.quitter_demande.connect(self.tout_fermer)
        fenetre.destroyed.connect(lambda _objet=None, f=fenetre: self._oublier(f))
        if self.fenetres:
            precedente = self.fenetres[-1].pos()
            fenetre.move(
                precedente.x() + DECALAGE_FENETRES_PX, precedente.y() + DECALAGE_FENETRES_PX
            )
        self.fenetres.append(fenetre)
        fenetre.show()
        return fenetre

    def demander_nouveau(self, parent: QWidget | None = None) -> FenetreDocument | None:
        """Ouvre la fenêtre de choix ; crée le document choisi (None si annulé)."""
        dialogue = DialogueNouveauDocument(parent)
        if dialogue.exec() and dialogue.choix is not None:
            return self.ouvrir(dialogue.choix)
        return None

    def tout_fermer(self) -> None:
        for fenetre in list(self.fenetres):
            fenetre.close()

    def _oublier(self, fenetre: FenetreDocument) -> None:
        if fenetre in self.fenetres:
            self.fenetres.remove(fenetre)
