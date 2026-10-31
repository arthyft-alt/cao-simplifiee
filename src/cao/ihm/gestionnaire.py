"""Gestionnaire des documents ouverts : une fenêtre par document.

Il ouvre la fenêtre « Nouveau document », crée la fenêtre du type choisi,
ouvre les fichiers, numérote les nouveaux documents (Pièce1, Pièce2…),
fait la sauvegarde automatique (toutes les 5 minutes) et propose la
récupération après une fermeture inattendue. C'est aussi lui qui, plus tard,
fera communiquer les documents entre eux (DOC-04).
"""

from pathlib import Path

from PySide6.QtCore import QObject, QStandardPaths, Qt, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

from cao.document.document import Document
from cao.fichiers import format_natif, recuperation
from cao.fichiers.types_documents import INFOS, CompteurDocuments, TypeDocument
from cao.ihm import textes
from cao.ihm.fenetre import FenetreDocument, dossier_documents, hauteur_ecran_disponible
from cao.ihm.nouveau_document import DialogueNouveauDocument
from cao.ihm.theme import appliquer_theme

DECALAGE_FENETRES_PX = 32  # chaque nouvelle fenêtre est décalée, pour les voir toutes
INTERVALLE_SAUVEGARDE_MS = recuperation.INTERVALLE_MINUTES * 60 * 1000


def dossier_recuperation_par_defaut() -> Path:
    """Dossier de données de l'application (Windows : AppData ; Linux : ~/.local/share)."""
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    return Path(base or Path.home() / ".cao-simplifiee") / "recuperation"


class GestionnaireDocuments(QObject):
    def __init__(self, avec_vue3d: bool = True, dossier_recuperation: Path | None = None) -> None:
        super().__init__()
        application = QApplication.instance()
        if isinstance(application, QApplication):
            appliquer_theme(application, hauteur_ecran_disponible())
        self.avec_vue3d = avec_vue3d
        self.compteur = CompteurDocuments()
        self.fenetres: list[FenetreDocument] = []
        self.dossier_recuperation = dossier_recuperation or dossier_recuperation_par_defaut()
        self.minuterie = QTimer(self)
        self.minuterie.setInterval(INTERVALLE_SAUVEGARDE_MS)
        self.minuterie.timeout.connect(self.sauvegarde_automatique)
        self.minuterie.start()

    # --- Création des fenêtres ---

    def ouvrir(self, type_document: TypeDocument) -> FenetreDocument:
        """Crée un nouveau document du type donné, dans sa propre fenêtre."""
        return self._creer_fenetre(
            Document(type_document, self.compteur.nom_suivant(type_document))
        )

    def _creer_fenetre(self, document: Document) -> FenetreDocument:
        fenetre = FenetreDocument(
            document.type_document, document.nom, self.avec_vue3d, document=document
        )
        fenetre.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        fenetre.nouveau_demande.connect(lambda: self.demander_nouveau(fenetre))
        fenetre.ouvrir_demande.connect(lambda: self.demander_ouverture(fenetre))
        fenetre.quitter_demande.connect(self.tout_fermer)
        # Fermeture normale (après enregistrement ou refus) : la copie de récupération est inutile.
        fenetre.destroyed.connect(lambda _objet=None, f=fenetre, d=document: self._oublier(f, d))
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
        if not dialogue.exec():
            return None
        if dialogue.ouvrir_fichier:
            return self.demander_ouverture(parent)
        return self.ouvrir(dialogue.choix) if dialogue.choix is not None else None

    # --- Ouverture de fichiers ---

    def fenetre_du_fichier(self, chemin: Path) -> FenetreDocument | None:
        cible = Path(chemin).resolve()
        for fenetre in self.fenetres:
            if fenetre.document.chemin and fenetre.document.chemin.resolve() == cible:
                return fenetre
        return None

    def ouvrir_fichier(self, chemin: Path, parent: QWidget | None = None) -> FenetreDocument | None:
        """Ouvre un fichier dans sa fenêtre ; s'il est déjà ouvert, montre sa fenêtre."""
        deja = self.fenetre_du_fichier(chemin)
        if deja is not None:
            deja.raise_()
            deja.activateWindow()
            return deja
        try:
            document = format_natif.ouvrir(Path(chemin))
        except format_natif.FichierInvalide as erreur:
            self.afficher_erreur(parent, textes.TITRE_ERREUR_OUVERTURE, str(erreur))
            return None
        return self._creer_fenetre(document)

    def demander_ouverture(self, parent: QWidget | None = None) -> FenetreDocument | None:
        chemin = self.choisir_fichier_a_ouvrir(parent)
        return self.ouvrir_fichier(chemin, parent) if chemin else None

    # Fenêtres de dialogue, remplacées par des réponses toutes faites dans les tests.

    def choisir_fichier_a_ouvrir(self, parent: QWidget | None) -> Path | None:
        extensions = " ".join(f"*{info.extension}" for info in INFOS.values())
        filtres = [f"{textes.FILTRE_TOUS} ({extensions})"]
        filtres += [f"{info.libelle} (*{info.extension})" for info in INFOS.values()]
        chemin, _filtre = QFileDialog.getOpenFileName(
            parent, textes.TITRE_OUVRIR, str(dossier_documents()), ";;".join(filtres)
        )
        return Path(chemin) if chemin else None

    def afficher_erreur(self, parent: QWidget | None, titre: str, message: str) -> None:
        QMessageBox.warning(parent, titre, message)

    def demander_recuperation(self, noms: list[str]) -> bool:
        boite = QMessageBox()
        boite.setWindowTitle(textes.TITRE_RECUPERATION)
        boite.setIcon(QMessageBox.Icon.Question)
        boite.setText(textes.question_recuperation(noms))
        recuperer = boite.addButton(textes.BOUTON_RECUPERER, QMessageBox.ButtonRole.AcceptRole)
        boite.addButton(textes.BOUTON_IGNORER, QMessageBox.ButtonRole.DestructiveRole)
        boite.setDefaultButton(recuperer)
        boite.exec()
        return boite.clickedButton() is recuperer

    # --- Sauvegarde automatique et récupération (DOC-03, §8.4) ---

    def sauvegarde_automatique(self) -> None:
        """Copie de récupération de chaque document modifié ; jamais bloquant."""
        for fenetre in self.fenetres:
            try:
                if fenetre.document.modifie:
                    recuperation.sauvegarder(fenetre.document, self.dossier_recuperation)
                else:
                    recuperation.supprimer(fenetre.document, self.dossier_recuperation)
            except OSError:
                pass  # disque plein, droits… : on réessaiera dans 5 minutes

    def proposer_recuperation(self) -> int:
        """Au lancement : propose de récupérer les copies laissées ; renvoie le nombre rouvert."""
        trouves = recuperation.lister(self.dossier_recuperation)
        if not trouves:
            return 0
        if not self.demander_recuperation([t.nom for t in trouves]):
            for element in trouves:
                element.fichier.unlink(missing_ok=True)
            return 0
        for element in trouves:
            self._creer_fenetre(recuperation.recuperer(element))
        return len(trouves)

    # --- Fermeture ---

    def tout_fermer(self) -> bool:
        """Ferme toutes les fenêtres ; s'arrête si l'utilisateur annule une fermeture."""
        for fenetre in list(self.fenetres):
            if not fenetre.close():
                return False
        return True

    def _oublier(self, fenetre: FenetreDocument, document: Document) -> None:
        recuperation.supprimer(document, self.dossier_recuperation)
        if fenetre in self.fenetres:
            self.fenetres.remove(fenetre)
