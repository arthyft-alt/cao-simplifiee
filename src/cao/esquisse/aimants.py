"""Aimantation du curseur pendant le tracé (inférence, exigence ESQ-04).

Quand le curseur passe près d'un élément remarquable, il y est attiré :
    1. un point existant ou l'origine (le plus fort) : le nouveau point sera
       confondu avec lui, le contour se ferme ;
    2. pour une ligne en cours : l'horizontale ou la verticale de son point de
       départ ; la ligne recevra la relation correspondante ;
    3. les axes du repère (passant par l'origine) : le point y restera attaché ;
    4. l'alignement horizontal ou vertical avec un point existant (simple aide
       au placement, sans relation, comme dans SolidWorks).
Chaque attraction est accompagnée de « guides » (traits pointillés) que
l'interface affiche pour montrer ce qui se passe.

Aucune dépendance à Qt ou OpenCascade.
"""

from dataclasses import dataclass, field
from enum import Enum

from cao.esquisse.esquisse import ORIGINE, Esquisse
from cao.esquisse.geometrie import Point2D, distance


class Axe(Enum):
    X = "x"  # axe horizontal du plan (v = 0)
    Y = "y"  # axe vertical du plan (u = 0)


class Orientation(Enum):
    HORIZONTALE = "horizontale"
    VERTICALE = "verticale"


@dataclass
class Aimantation:
    position: Point2D  # position corrigée par les aimants
    accroche: str | None = None  # point existant attrapé
    sur_axe: Axe | None = None  # point posé sur un axe du repère
    orientation: Orientation | None = None  # la ligne en cours devient horizontale / verticale
    guides: list[tuple[Point2D, Point2D]] = field(default_factory=list)  # traits pointillés

    @property
    def active(self) -> bool:
        return bool(self.accroche or self.sur_axe or self.orientation or self.guides)


def aimanter(
    esquisse: Esquisse,
    souris: Point2D,
    tolerance: float,
    depart: Point2D | None = None,
) -> Aimantation:
    """Position aimantée du curseur. `tolerance` en mm (environ 10 pixels à l'écran) ;
    `depart` : point de départ de la ligne en cours, s'il y en a une."""
    # 1. Points existants et origine.
    candidats = [p.id for p in esquisse.points()] + [ORIGINE]
    proche = min(candidats, key=lambda i: distance(esquisse.position(i), souris))
    if distance(esquisse.position(proche), souris) <= tolerance:
        return Aimantation(esquisse.position(proche), accroche=proche)

    x, y = souris.x, souris.y
    resultat = Aimantation(souris)
    marge = 2 * tolerance  # longueur dépassant le curseur pour les guides

    # 2. Ligne en cours presque horizontale ou presque verticale.
    pris_x = pris_y = False
    if depart is not None and distance(depart, souris) > tolerance:
        if abs(y - depart.y) <= tolerance:
            y, pris_y = depart.y, True
            resultat.orientation = Orientation.HORIZONTALE
        elif abs(x - depart.x) <= tolerance:
            x, pris_x = depart.x, True
            resultat.orientation = Orientation.VERTICALE

    # 3. Axes du repère.
    if not pris_y and abs(y) <= tolerance:
        y, pris_y = 0.0, True
        resultat.sur_axe = Axe.X
        resultat.guides.append(
            (Point2D(min(0.0, x) - marge, 0.0), Point2D(max(0.0, x) + marge, 0.0))
        )
    elif not pris_x and abs(x) <= tolerance:
        x, pris_x = 0.0, True
        resultat.sur_axe = Axe.Y
        resultat.guides.append(
            (Point2D(0.0, min(0.0, y) - marge), Point2D(0.0, max(0.0, y) + marge))
        )

    # 4. Alignement avec un point existant (aide au placement, sans relation).
    points = [esquisse.position(p.id) for p in esquisse.points()]
    if not pris_x:
        alignes = [p for p in points if abs(p.x - x) <= tolerance]
        if alignes:
            repere = min(alignes, key=lambda p: abs(p.x - x))
            x, pris_x = repere.x, True
            resultat.guides.append((repere, Point2D(x, y)))
    if not pris_y:
        alignes = [p for p in points if abs(p.y - y) <= tolerance]
        if alignes:
            repere = min(alignes, key=lambda p: abs(p.y - y))
            y = repere.y
            resultat.guides.append((repere, Point2D(x, y)))

    resultat.position = Point2D(x, y)
    if resultat.orientation is not None and depart is not None:
        # Le guide dépasse le curseur : sinon l'aperçu de la ligne le cacherait entièrement.
        ecart = resultat.position - depart
        longueur = ecart.norme() or 1.0
        bout = resultat.position + ecart.fois(marge * 2 / longueur)
        resultat.guides.insert(0, (depart, bout))
    return resultat
