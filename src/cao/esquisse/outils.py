"""Outils de tracé à la souris (GEO-01 à GEO-04), indépendants de l'affichage.

Chaque outil reçoit des clics déjà convertis en coordonnées du plan (mm) et,
quand le tracé est complet, renvoie une *modification* : une fonction qui
ajoute l'entité à l'esquisse (elle sera exécutée par une commande annulable).
Il fournit aussi un *aperçu* (ce qu'il faut dessiner pendant que la souris bouge).

Accrochage : si le clic tombe près d'un point existant, l'interface passe
l'identifiant de ce point (`accroche`). La ligne utilise alors ce point (les deux
lignes sont reliées) ; les autres outils, qui créent leurs propres points,
ajoutent une relation « coïncidente » avec lui.

Aucune dépendance à Qt ou OpenCascade : testable sans écran.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field

from cao.esquisse.aimants import Axe, Orientation
from cao.esquisse.esquisse import ORIGINE, Arc, Esquisse, GenreRelation, Ligne
from cao.esquisse.geometrie import (
    TOLERANCE,
    GeometrieImpossible,
    Point2D,
    arc_trois_points,
    distance,
    rectangle_deux_coins,
)

Modification = Callable[[Esquisse], object]


@dataclass
class Apercu:
    """Tracé provisoire, affiché en pointillés pendant le mouvement de la souris."""

    lignes: list[tuple[Point2D, Point2D]] = field(default_factory=list)
    cercles: list[tuple[Point2D, float]] = field(default_factory=list)
    arcs: list[tuple[Point2D, Point2D, Point2D]] = field(default_factory=list)  # centre, début, fin

    @property
    def vide(self) -> bool:
        return not (self.lignes or self.cercles or self.arcs)


@dataclass(frozen=True)
class Clic:
    """Clic sur le plan, déjà corrigé par les aimants (voir esquisse/aimants.py)."""

    position: Point2D
    accroche: str | None = None  # point existant attrapé
    sur_axe: Axe | None = None  # point posé sur un axe du repère
    orientation: Orientation | None = None  # la ligne qui finit ici est horizontale/verticale


def _relier(esquisse: Esquisse, nouveau: str, clic: Clic) -> None:
    """Attache un point créé par l'outil à ce que le clic a attrapé :
    coïncidence avec un point existant, ou maintien sur un axe du repère."""
    if clic.accroche is not None and clic.accroche != nouveau:
        esquisse.ajouter_relation(GenreRelation.COINCIDENTE, nouveau, clic.accroche)
    elif clic.accroche is None and clic.sur_axe == Axe.X:
        esquisse.ajouter_relation(GenreRelation.HORIZONTALE, nouveau, ORIGINE)
    elif clic.accroche is None and clic.sur_axe == Axe.Y:
        esquisse.ajouter_relation(GenreRelation.VERTICALE, nouveau, ORIGINE)


def _point_le_plus_proche(esquisse: Esquisse, ids: list[str], position: Point2D) -> str:
    return min(ids, key=lambda i: distance(esquisse.position(i), position))


class Outil(ABC):
    nom: str = ""

    def __init__(self) -> None:
        self.clics: list[Clic] = []

    @property
    def etape(self) -> int:
        """Nombre de clics déjà donnés pour l'entité en cours (sert aux consignes)."""
        return len(self.clics)

    @property
    def en_cours(self) -> bool:
        return bool(self.clics)

    def abandonner(self) -> None:
        """Échap : oublie le tracé en cours."""
        self.clics.clear()

    def terminer(self) -> None:
        """Double-clic ou clic droit : termine une suite (utile pour les lignes chaînées)."""
        self.clics.clear()

    @abstractmethod
    def clic(self, clic: Clic) -> Modification | None:
        """Nouveau clic ; renvoie la modification à faire quand l'entité est complète."""

    def applique(self, esquisse: Esquisse, resultat: object) -> None:  # noqa: B027
        """Appelé après la modification (pour enchaîner le tracé suivant)."""

    @abstractmethod
    def apercu(self, souris: Point2D) -> Apercu: ...

    def point_de_depart(self) -> Point2D | None:
        """Point d'où part la ligne en cours (pour l'aimant horizontal / vertical)."""
        return None


class OutilLigne(Outil):
    """Lignes chaînées : chaque clic ajoute une ligne qui part du bout de la précédente.
    La suite s'arrête par double-clic, clic droit, Échap, ou en revenant sur son premier point."""

    nom = "ligne"

    def __init__(self) -> None:
        super().__init__()
        self.depart: str | Point2D | None = None  # point d'où part la prochaine ligne
        self.premier: str | None = None  # premier point de la suite (pour la refermer)
        self.position_depart: Point2D | None = None
        self.clic_depart: Clic | None = None  # pour attacher le tout premier point

    @property
    def etape(self) -> int:
        return 0 if self.depart is None else 1

    @property
    def en_cours(self) -> bool:
        return self.depart is not None

    def abandonner(self) -> None:
        self.depart = self.premier = self.position_depart = self.clic_depart = None

    terminer = abandonner

    def point_de_depart(self) -> Point2D | None:
        return self.position_depart

    def clic(self, clic: Clic) -> Modification | None:
        cible: str | Point2D = clic.accroche or clic.position
        if self.depart is None:
            self.depart, self.position_depart, self.clic_depart = cible, clic.position, clic
            return None
        depart = self.depart
        clic_depart = self.clic_depart
        if (
            self.position_depart is not None
            and distance(self.position_depart, clic.position) < TOLERANCE
        ):
            return None  # deux clics au même endroit : rien à tracer

        def modification(e: Esquisse) -> str:
            identifiant = e.ajouter_ligne(depart, cible)
            ligne = e[identifiant]
            assert isinstance(ligne, Ligne)
            if clic.orientation == Orientation.HORIZONTALE:
                e.ajouter_relation(GenreRelation.HORIZONTALE, identifiant)
            elif clic.orientation == Orientation.VERTICALE:
                e.ajouter_relation(GenreRelation.VERTICALE, identifiant)
            if clic_depart is not None and not isinstance(depart, str):
                _relier(e, ligne.debut, clic_depart)  # tout premier point de la suite
            if not isinstance(cible, str):
                _relier(e, ligne.fin, clic)
            return identifiant

        return modification

    def applique(self, esquisse: Esquisse, resultat: object) -> None:
        ligne = esquisse[str(resultat)]
        assert isinstance(ligne, Ligne)
        if self.premier is None:
            self.premier = ligne.debut
        if ligne.fin == self.premier:  # contour refermé : la suite est finie
            self.abandonner()
            return
        self.depart, self.position_depart = ligne.fin, esquisse.position(ligne.fin)
        self.clic_depart = None  # les points suivants sont déjà attachés

    def apercu(self, souris: Point2D) -> Apercu:
        if self.position_depart is None:
            return Apercu()
        return Apercu(lignes=[(self.position_depart, souris)])


class OutilRectangle(Outil):
    """Rectangle par deux coins opposés, avec ses relations horizontales et verticales
    (comme dans SolidWorks) : seules la position et les deux dimensions restent libres."""

    nom = "rectangle"

    def clic(self, clic: Clic) -> Modification | None:
        self.clics.append(clic)
        if len(self.clics) < 2:
            return None
        premier, second = self.clics
        self.clics = []

        def modification(e: Esquisse) -> list[str]:
            cotes = e.ajouter_rectangle(premier.position, second.position)
            bas, droite, haut, gauche = cotes
            for cote in (bas, haut):
                e.ajouter_relation(GenreRelation.HORIZONTALE, cote)
            for cote in (droite, gauche):
                e.ajouter_relation(GenreRelation.VERTICALE, cote)
            coins = [e[c].debut for c in cotes]  # type: ignore[union-attr]
            for c in (premier, second):
                _relier(e, _point_le_plus_proche(e, coins, c.position), c)
            return cotes

        return modification

    def apercu(self, souris: Point2D) -> Apercu:
        if not self.clics:
            return Apercu()
        try:
            a, b, c, d = rectangle_deux_coins(self.clics[0].position, souris)
        except GeometrieImpossible:
            return Apercu()
        return Apercu(lignes=[(a, b), (b, c), (c, d), (d, a)])


class OutilCercle(Outil):
    """Cercle : centre, puis un point du cercle (qui donne le rayon)."""

    nom = "cercle"

    def clic(self, clic: Clic) -> Modification | None:
        self.clics.append(clic)
        if len(self.clics) < 2:
            return None
        centre, bord = self.clics
        self.clics = []
        rayon = distance(centre.position, bord.position)
        if rayon < TOLERANCE:
            return None
        centre_ref: str | Point2D = centre.accroche or centre.position

        def modification(e: Esquisse) -> str:
            identifiant = e.ajouter_cercle(centre_ref, rayon)
            if centre.accroche is None:
                _relier(e, e[identifiant].centre, centre)  # type: ignore[union-attr]
            return identifiant

        return modification

    def apercu(self, souris: Point2D) -> Apercu:
        if not self.clics:
            return Apercu()
        centre = self.clics[0].position
        rayon = distance(centre, souris)
        return Apercu(cercles=[(centre, rayon)]) if rayon > TOLERANCE else Apercu()


class OutilArc(Outil):
    """Arc par trois points : début, fin, puis un point de passage (comme SolidWorks)."""

    nom = "arc"

    def clic(self, clic: Clic) -> Modification | None:
        self.clics.append(clic)
        if len(self.clics) < 3:
            return None
        debut, fin, passage = self.clics
        self.clics = []

        def modification(e: Esquisse) -> str:
            identifiant = e.ajouter_arc_trois_points(debut.position, passage.position, fin.position)
            arc = e[identifiant]
            assert isinstance(arc, Arc)
            for c in (debut, fin):
                _relier(e, _point_le_plus_proche(e, [arc.debut, arc.fin], c.position), c)
            return identifiant

        return modification

    def apercu(self, souris: Point2D) -> Apercu:
        if len(self.clics) == 1:
            return Apercu(lignes=[(self.clics[0].position, souris)])
        if len(self.clics) == 2:
            try:
                centre, d, f = arc_trois_points(
                    self.clics[0].position, souris, self.clics[1].position
                )
            except GeometrieImpossible:
                return Apercu(lignes=[(self.clics[0].position, self.clics[1].position)])
            return Apercu(arcs=[(centre, d, f)])
        return Apercu()


OUTILS: dict[str, type[Outil]] = {
    "ligne": OutilLigne,
    "rectangle": OutilRectangle,
    "cercle": OutilCercle,
    "arc": OutilArc,
}
