"""Contenu d'un document pièce : ses esquisses (lot 2), puis ses fonctions (lot 3).

Toute modification d'une esquisse passe par `CommandeEsquisse`, qui retient
l'état de l'esquisse avant et après : Ctrl+Z annule ainsi n'importe quelle
modification (tracé, relation, cote, suppression) sans code d'annulation propre
à chacune.
"""

from collections.abc import Callable
from typing import Any

from cao.document.historique import Commande
from cao.esquisse.esquisse import Esquisse


class Piece:
    def __init__(self) -> None:
        self.esquisses: list[Esquisse] = []

    def nom_esquisse_suivant(self) -> str:
        numeros = [
            int(e.nom[len("Esquisse") :])
            for e in self.esquisses
            if e.nom.startswith("Esquisse") and e.nom[len("Esquisse") :].isdigit()
        ]
        return f"Esquisse{max(numeros, default=0) + 1}"

    def esquisse(self, nom: str) -> Esquisse:
        for esquisse in self.esquisses:
            if esquisse.nom == nom:
                return esquisse
        raise KeyError(nom)

    def vers_dict(self) -> dict[str, Any]:
        return {"esquisses": [e.vers_dict() for e in self.esquisses]}

    @classmethod
    def depuis_dict(cls, donnees: dict[str, Any]) -> "Piece":
        piece = cls()
        piece.esquisses = [Esquisse.depuis_dict(e) for e in donnees.get("esquisses", [])]
        return piece


def restaurer(esquisse: Esquisse, etat: dict[str, Any]) -> None:
    """Remet une esquisse dans un état enregistré, en gardant le même objet."""
    copie = Esquisse.depuis_dict(etat)
    esquisse.nom, esquisse.plan = copie.nom, copie.plan
    esquisse.entites, esquisse.relations, esquisse.cotes = (
        copie.entites,
        copie.relations,
        copie.cotes,
    )
    esquisse._compteurs = copie._compteurs


class CommandeAjouterEsquisse(Commande):
    def __init__(self, piece: Piece, esquisse: Esquisse) -> None:
        self.piece, self.esquisse = piece, esquisse
        self.libelle = f"Créer {esquisse.nom}"

    def executer(self) -> None:
        self.piece.esquisses.append(self.esquisse)

    def annuler(self) -> None:
        self.piece.esquisses.remove(self.esquisse)


class CommandeEsquisse(Commande):
    """Modification quelconque d'une esquisse, annulable par retour à l'état précédent.

    `modification` est appelée une seule fois, à la première exécution ; si elle
    échoue (tracé impossible…), l'esquisse est remise dans son état d'avant et
    l'erreur est transmise.
    """

    def __init__(
        self, esquisse: Esquisse, libelle: str, modification: Callable[[Esquisse], object]
    ) -> None:
        self.esquisse = esquisse
        self.libelle = libelle
        self.modification: Callable[[Esquisse], object] | None = modification
        self.avant = esquisse.vers_dict()
        self.apres: dict[str, Any] | None = None
        self.resultat: object = None

    def executer(self) -> None:
        if self.modification is not None:
            try:
                self.resultat = self.modification(self.esquisse)
            except Exception:
                restaurer(self.esquisse, self.avant)
                raise
            self.modification = None
            self.apres = self.esquisse.vers_dict()
        elif self.apres is not None:
            restaurer(self.esquisse, self.apres)

    def annuler(self) -> None:
        restaurer(self.esquisse, self.avant)
