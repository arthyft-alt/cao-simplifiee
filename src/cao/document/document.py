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
from cao.document.unites import Unites
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
        # Contenu propre au type : objet de travail (`modele`, ex. Piece) et données
        # brutes qui ne lui appartiennent pas (`contenu`), toutes deux enregistrées.
        self.modele = _creer_modele(type_document, {})
        self.contenu: dict[str, Any] = {}
        self.unites = Unites()  # unités d'affichage et de saisie (COT-06)

    def vers_dict(self) -> dict[str, Any]:
        """Données à écrire dans le fichier (voir docs/format_fichier.md)."""
        contenu = dict(self.contenu)
        if self.modele is not None:
            contenu.update(self.modele.vers_dict())
        contenu["unites"] = self.unites.vers_dict()
        return {"type": self.type_document.value, "nom": self.nom, "contenu": contenu}

    @classmethod
    def depuis_dict(cls, donnees: dict[str, Any]) -> "Document":
        document = cls(TypeDocument(donnees["type"]), donnees["nom"])
        contenu = dict(donnees.get("contenu", {}))
        document.modele = _creer_modele(document.type_document, contenu)
        document.unites = Unites.depuis_dict(dict(contenu.get("unites", {})))
        cles_modele = (*_CLES_MODELE.get(document.type_document, ()), "unites")
        document.contenu = {k: v for k, v in contenu.items() if k not in cles_modele}
        return document

    @property
    def modifie(self) -> bool:
        return self.historique.modifie

    def renommer(self, nouveau_nom: str) -> None:
        """Renomme le document, de façon annulable."""
        nom = verifier_nom(nouveau_nom)
        if nom != self.nom:
            self.historique.executer(CommandeRenommer(self, nom))


# Clés de `contenu` gérées par l'objet de travail de chaque type.
_CLES_MODELE: dict[TypeDocument, tuple[str, ...]] = {TypeDocument.PIECE: ("esquisses",)}


def _creer_modele(type_document: TypeDocument, contenu: dict[str, Any]) -> Any:
    """Objet de travail du document : une Piece pour une pièce (assemblage et plan : lots 4-5)."""
    if type_document == TypeDocument.PIECE:
        from cao.piece.piece import Piece  # import ici : la pièce dépend du document

        return Piece.depuis_dict(contenu)
    return None


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


class CommandeUnites(Commande):
    """Changement d'unité ou de précision d'affichage (annulable)."""

    def __init__(self, document: Document, unites: Unites) -> None:
        self.document = document
        self.avant = document.unites
        self.apres = unites
        self.libelle = f"Unités : {unites.longueur.value}, {unites.decimales} décimales"

    def executer(self) -> None:
        self.document.unites = self.apres

    def annuler(self) -> None:
        self.document.unites = self.avant
