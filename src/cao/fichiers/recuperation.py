"""Sauvegarde automatique et récupération après fermeture inattendue (DOC-03, §8.4).

Toutes les 5 minutes, chaque document modifié est copié dans un dossier de
récupération (et non dans son propre fichier : on n'écrase jamais le travail
de l'utilisateur sans qu'il l'ait demandé). À la fermeture normale d'un
document, sa copie est effacée. S'il en reste au lancement suivant, c'est que
le logiciel s'est arrêté brutalement : on propose de les récupérer.

Le dossier est fourni par l'interface (emplacement standard du système,
QStandardPaths), ce module ne dépend donc pas de Qt.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cao.document.document import Document
from cao.fichiers import format_natif

INTERVALLE_MINUTES = 5


@dataclass(frozen=True)
class Recuperable:
    fichier: Path  # copie de récupération
    nom: str  # nom du document au moment de la copie
    chemin_origine: Path | None  # fichier d'origine (None : jamais enregistré)
    date: datetime | None


def fichier_de(document: Document, dossier: Path) -> Path:
    return Path(dossier) / f"{document.identifiant}{format_natif.extension(document.type_document)}"


def sauvegarder(document: Document, dossier: Path) -> Path:
    """Copie de récupération du document (ne change ni son état ni son fichier)."""
    origine = str(document.chemin) if document.chemin else None
    fichier = fichier_de(document, dossier)
    format_natif.ecrire(document, fichier, {"recuperation": {"chemin_origine": origine}})
    return fichier


def supprimer(document: Document, dossier: Path) -> None:
    fichier_de(document, dossier).unlink(missing_ok=True)


def lister(dossier: Path) -> list[Recuperable]:
    """Copies laissées par une fermeture inattendue (les fichiers illisibles sont ignorés)."""
    dossier = Path(dossier)
    if not dossier.is_dir():
        return []
    trouves = []
    for fichier in sorted(dossier.iterdir()):
        if format_natif.type_depuis_extension(fichier) is None:
            continue
        try:
            donnees = format_natif.lire_description(fichier)
        except format_natif.FichierInvalide:
            continue
        origine = donnees.get("recuperation", {}).get("chemin_origine")
        try:
            date: datetime | None = datetime.fromisoformat(donnees["enregistre_le"])
        except (KeyError, ValueError):
            date = None
        trouves.append(
            Recuperable(fichier, donnees["nom"], Path(origine) if origine else None, date)
        )
    return trouves


def recuperer(element: Recuperable) -> Document:
    """Rouvre une copie : le document reprend son fichier d'origine et reste « modifié »
    (l'utilisateur doit l'enregistrer pour conserver le travail récupéré). La copie est effacée."""
    document = format_natif.ouvrir(element.fichier)
    document.nom = element.nom
    document.chemin = element.chemin_origine
    document.historique.oublier_enregistrement()
    element.fichier.unlink(missing_ok=True)
    return document
