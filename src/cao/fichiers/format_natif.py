"""Format de fichier natif (exigences DOC-01, DOC-07, TEC-10). Voir docs/format_fichier.md.

Un document = une archive ZIP contenant :
    document.json   description lisible du document (texte UTF-8, JSON)
    geometrie/      formes au format B-Rep d'OpenCascade (à partir du lot 3)

Règles :
    - écriture « atomique » : on écrit un fichier temporaire puis on le renomme ;
      un plantage pendant l'enregistrement ne détruit jamais l'ancien fichier (§8.4) ;
    - fichiers identiques sous Windows et Linux : UTF-8, fins de ligne « \\n »,
      clés triées, aucun chemin absolu dans le contenu (TEC-10) ;
    - compatibilité ascendante : chaque fichier porte un numéro de version de
      format ; une version N+1 du logiciel sait lire les fichiers de la version N.
"""

import json
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cao import NOM_APPLICATION, __version__
from cao.document.document import Document
from cao.fichiers.types_documents import INFOS, TypeDocument

IDENTIFIANT_FORMAT = "cao-simplifiee"
VERSION_FORMAT = 1
NOM_DESCRIPTION = "document.json"


class FichierInvalide(Exception):
    """Le fichier ne peut pas être ouvert ; le message est destiné à l'utilisateur."""


def extension(type_document: TypeDocument) -> str:
    return INFOS[type_document].extension


def type_depuis_extension(chemin: Path) -> TypeDocument | None:
    for type_document, info in INFOS.items():
        if chemin.suffix.lower() == info.extension:
            return type_document
    return None


def description(document: Document, supplement: dict[str, Any] | None = None) -> dict[str, Any]:
    """Contenu de document.json."""
    donnees: dict[str, Any] = {
        "format": IDENTIFIANT_FORMAT,
        "version_format": VERSION_FORMAT,
        "application": f"{NOM_APPLICATION} {__version__}",
        "enregistre_le": datetime.now(UTC).isoformat(timespec="seconds"),
        **document.vers_dict(),
    }
    if supplement:
        donnees.update(supplement)
    return donnees


def ecrire(document: Document, chemin: Path, supplement: dict[str, Any] | None = None) -> None:
    """Écrit le document dans `chemin`, sans jamais abîmer un fichier existant en cas d'échec."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    texte = json.dumps(
        description(document, supplement), ensure_ascii=False, indent=2, sort_keys=True
    )
    temporaire = chemin.with_name(chemin.name + ".tmp")
    try:
        with zipfile.ZipFile(temporaire, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(NOM_DESCRIPTION, texte + "\n")
        os.replace(temporaire, chemin)  # remplacement en une seule opération
    finally:
        temporaire.unlink(missing_ok=True)


def enregistrer(document: Document, chemin: Path) -> None:
    """Enregistre le document : il prend le nom du fichier et n'est plus « modifié »."""
    chemin = Path(chemin)
    ecrire(document, chemin)
    document.chemin = chemin
    document.nom = chemin.stem
    document.historique.marquer_enregistre()


def lire_description(chemin: Path) -> dict[str, Any]:
    """Lit et vérifie document.json ; FichierInvalide avec un message clair sinon."""
    chemin = Path(chemin)
    if not chemin.is_file():
        raise FichierInvalide(f"Le fichier « {chemin.name} » est introuvable.")
    try:
        with zipfile.ZipFile(chemin) as archive:
            donnees = json.loads(archive.read(NOM_DESCRIPTION).decode("utf-8"))
    except (zipfile.BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError) as erreur:
        raise FichierInvalide(
            f"« {chemin.name} » n'est pas un document de {NOM_APPLICATION} ou il est abîmé."
        ) from erreur
    if not isinstance(donnees, dict) or donnees.get("format") != IDENTIFIANT_FORMAT:
        raise FichierInvalide(f"« {chemin.name} » n'est pas un document de {NOM_APPLICATION}.")
    version = donnees.get("version_format")
    if not isinstance(version, int) or version > VERSION_FORMAT:
        raise FichierInvalide(
            f"« {chemin.name} » a été créé avec une version plus récente du logiciel. "
            "Mettez le logiciel à jour pour l'ouvrir."
        )
    if donnees.get("type") not in {t.value for t in TypeDocument}:
        raise FichierInvalide(f"« {chemin.name} » : type de document inconnu.")
    return donnees


def ouvrir(chemin: Path) -> Document:
    """Lit un document enregistré ; il n'est pas « modifié » après ouverture."""
    chemin = Path(chemin)
    document = Document.depuis_dict(lire_description(chemin))
    document.nom = chemin.stem
    document.chemin = chemin
    return document
