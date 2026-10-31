"""Les trois types de documents du logiciel (exigence DOC-01).

Comme dans SolidWorks, une pièce, un assemblage et une mise en plan sont trois
documents distincts, chacun ouvert dans sa propre fenêtre avec sa propre
interface. Ils communiquent par références de fichiers (DOC-04) :
un assemblage utilise des pièces, une mise en plan représente une pièce
ou un assemblage.

Ce module ne dépend pas de Qt : il est testable sans fenêtre.
"""

from dataclasses import dataclass
from enum import Enum


class TypeDocument(Enum):
    PIECE = "piece"
    ASSEMBLAGE = "assemblage"
    MISE_EN_PLAN = "mise_en_plan"


@dataclass(frozen=True)
class InfoType:
    libelle: str  # nom affiché (« Pièce »)
    nom_base: str  # base du nom par défaut (« Pièce » -> « Pièce1 »)
    extension: str  # PROVISOIRE : extension de fichier, à confirmer à l'étape 1.6
    vue_3d: bool  # True : zone graphique 3D ; False : feuille de dessin 2D
    description: str  # phrase d'explication dans la fenêtre « Nouveau document »


INFOS: dict[TypeDocument, InfoType] = {
    TypeDocument.PIECE: InfoType(
        "Pièce",
        "Pièce",
        ".caop",
        True,
        "Modéliser une pièce à partir d'esquisses et de fonctions volumiques.",
    ),
    TypeDocument.ASSEMBLAGE: InfoType(
        "Assemblage",
        "Assemblage",
        ".caoa",
        True,
        "Positionner des pièces les unes par rapport aux autres par des contraintes.",
    ),
    TypeDocument.MISE_EN_PLAN: InfoType(
        "Mise en plan",
        "Plan",
        ".caom",
        False,
        "Dessin technique 2D d'une pièce ou d'un assemblage : vues, cotes, cartouche.",
    ),
}


class CompteurDocuments:
    """Donne les noms par défaut des nouveaux documents : Pièce1, Pièce2, Assemblage1…

    Chaque type a sa propre numérotation, comme dans SolidWorks.
    """

    def __init__(self) -> None:
        self._compteurs: dict[TypeDocument, int] = {t: 0 for t in TypeDocument}

    def nom_suivant(self, type_document: TypeDocument) -> str:
        self._compteurs[type_document] += 1
        return f"{INFOS[type_document].nom_base}{self._compteurs[type_document]}"
