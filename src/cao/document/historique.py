"""Annuler / rétablir (cahier des charges §2.1 : « réversible », Ctrl+Z / Ctrl+Y).

Principe (patron « commande ») : chaque modification du document est un objet
`Commande` qui sait se faire (`executer`) et se défaire (`annuler`). La
`PileAnnulation` range les commandes faites ; annuler défait la dernière,
rétablir la refait. Le nombre de pas est illimité pendant la séance.

Règle de fiabilité (§8.4) : si une commande échoue, la pile n'est pas modifiée
et l'erreur est transmise ; le document reste dans l'état d'avant.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from contextlib import contextmanager


class Commande(ABC):
    """Une modification annulable du document."""

    libelle: str = ""  # texte affiché : « Annuler Renommer en « Support » »

    @abstractmethod
    def executer(self) -> None: ...

    @abstractmethod
    def annuler(self) -> None: ...


class CommandeGroupee(Commande):
    """Plusieurs commandes annulées et rétablies d'un seul coup."""

    def __init__(self, libelle: str) -> None:
        self.libelle = libelle
        self.commandes: list[Commande] = []

    def executer(self) -> None:  # rétablir : refaire dans l'ordre
        for commande in self.commandes:
            commande.executer()

    def annuler(self) -> None:  # annuler : défaire dans l'ordre inverse
        for commande in reversed(self.commandes):
            commande.annuler()


class PileAnnulation:
    def __init__(self) -> None:
        self._faites: list[Commande] = []  # la dernière faite est en fin de liste
        self._defaites: list[Commande] = []  # la dernière défaite est en fin de liste
        self._groupe: CommandeGroupee | None = None
        self._observateurs: list[Callable[[], None]] = []
        # Nombre de commandes faites au moment du dernier enregistrement
        # (None : l'état enregistré n'est plus atteignable).
        self._repere_enregistrement: int | None = 0

    # --- Observation : l'interface est prévenue à chaque changement ---

    def abonner(self, observateur: Callable[[], None]) -> None:
        self._observateurs.append(observateur)

    def _prevenir(self) -> None:
        for observateur in self._observateurs:
            observateur()

    # --- Faire, annuler, rétablir ---

    def executer(self, commande: Commande) -> None:
        """Fait la commande et la range. Si elle échoue, rien n'est rangé."""
        commande.executer()
        if self._groupe is not None:
            self._groupe.commandes.append(commande)
            return
        self._ranger(commande)

    def _ranger(self, commande: Commande) -> None:
        self._faites.append(commande)
        if self._defaites:
            # Une nouvelle action efface ce qui pouvait être rétabli.
            if self._repere_enregistrement is not None and self._repere_enregistrement >= len(
                self._faites
            ):
                self._repere_enregistrement = None
            self._defaites.clear()
        self._prevenir()

    def annuler(self) -> bool:
        """Défait la dernière commande ; False s'il n'y a rien à annuler."""
        if not self._faites:
            return False
        commande = self._faites[-1]
        commande.annuler()  # en cas d'erreur, la pile reste inchangée
        self._defaites.append(self._faites.pop())
        self._prevenir()
        return True

    def retablir(self) -> bool:
        """Refait la dernière commande annulée ; False s'il n'y a rien à rétablir."""
        if not self._defaites:
            return False
        commande = self._defaites[-1]
        commande.executer()
        self._faites.append(self._defaites.pop())
        self._prevenir()
        return True

    @contextmanager
    def groupe(self, libelle: str) -> Iterator[None]:
        """Regroupe les commandes faites dans le bloc `with` en un seul pas d'annulation.

        Si une commande du bloc échoue, celles déjà faites sont défaites.
        """
        if self._groupe is not None:  # groupe dans un groupe : on reste dans le premier
            yield
            return
        self._groupe = CommandeGroupee(libelle)
        try:
            yield
        except BaseException:
            groupe, self._groupe = self._groupe, None
            groupe.annuler()
            raise
        groupe, self._groupe = self._groupe, None
        if groupe.commandes:
            self._ranger(groupe)

    # --- État, pour l'interface ---

    @property
    def peut_annuler(self) -> bool:
        return bool(self._faites)

    @property
    def peut_retablir(self) -> bool:
        return bool(self._defaites)

    @property
    def libelle_annuler(self) -> str:
        return self._faites[-1].libelle if self._faites else ""

    @property
    def libelle_retablir(self) -> str:
        return self._defaites[-1].libelle if self._defaites else ""

    @property
    def modifie(self) -> bool:
        """Le document diffère-t-il de sa dernière version enregistrée ?"""
        return self._repere_enregistrement != len(self._faites)

    def marquer_enregistre(self) -> None:
        self._repere_enregistrement = len(self._faites)
        self._prevenir()
