"""Le document ouvert dans une fenêtre : type, nom et historique.

Le contenu propre à chaque type (esquisses et fonctions d'une pièce,
composants d'un assemblage, vues d'un plan) s'y ajoutera aux lots 2 à 5.
Toute modification passe par une `Commande` exécutée par `historique`,
pour pouvoir être annulée.
"""

import uuid
from pathlib import Path
from typing import Any

from cao.document.historique import Commande, PileAnnulation
from cao.fichiers.types_documents import TypeDocument


class NomInvalide(ValueError):
    """Nom de document vide ou contenant des caractères interdits dans un nom de fichier."""


CARACTERES_INTERDITS = set('\\/:*?"<>|')


def verifier_nom(nom: str) -> str:
    """Nom nettoyé (espaces de début et de fin retirés) ; NomInvalide s'il ne convient pas."""
    propre = nom.strip()
    if not propre:
        raise NomInvalide("Le nom ne peut pas être vide.")
    interdits = sorted(CARACTERES_INTERDITS & set(propre))
    if interdits:
        raise NomInvalide(f"Caractères interdits dans un nom : {' '.join(interdits)}")
    return propre


class Document:
    def __init__(self, type_document: TypeDocument, nom: str) -> None:
        self.type_document = type_document
        self.nom = verifier_nom(nom)
        self.historique = PileAnnulation()
        self.chemin: Path | None = None  # fichier où il est enregistré (None : jamais)
        # Identifiant de séance, pour nommer son fichier de récupération (non enregistré).
        self.identifiant = uuid.uuid4().hex
        # Contenu propre au type (esquisses, fonctions, composants, vues…) : lots 2 à 5.
        self.contenu: dict[str, Any] = {}

    def vers_dict(self) -> dict[str, Any]:
        """Données à écrire dans le fichier (voir docs/format_fichier.md)."""
        return {"type": self.type_document.value, "nom": self.nom, "contenu": self.contenu}

    @classmethod
    def depuis_dict(cls, donnees: dict[str, Any]) -> "Document":
        document = cls(TypeDocument(donnees["type"]), donnees["nom"])
        document.contenu = dict(donnees.get("contenu", {}))
        return document

    @property
    def modifie(self) -> bool:
        return self.historique.modifie

    def renommer(self, nouveau_nom: str) -> None:
        """Renomme le document, de façon annulable."""
        nom = verifier_nom(nouveau_nom)
        if nom != self.nom:
            self.historique.executer(CommandeRenommer(self, nom))


class CommandeRenommer(Commande):
    def __init__(self, document: Document, nouveau_nom: str) -> None:
        self.document = document
        self.ancien_nom = document.nom
        self.nouveau_nom = nouveau_nom
        self.libelle = f"Renommer en « {nouveau_nom} »"

    def executer(self) -> None:
        self.document.nom = self.nouveau_nom

    def annuler(self) -> None:
        self.document.nom = self.ancien_nom
