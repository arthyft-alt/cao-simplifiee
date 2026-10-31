"""Calculs de géométrie plane utilisés par les modes de tracé de l'esquisse.

Coordonnées en millimètres dans le repère du plan d'esquisse (u, v).
Angles en radians, sens trigonométrique (inverse des aiguilles d'une montre).
Aucune dépendance : ni Qt, ni OpenCascade.
"""

import math
from typing import NamedTuple

TOLERANCE = 1e-9  # mm : en dessous, deux longueurs sont considérées égales à zéro


class Point2D(NamedTuple):
    x: float
    y: float

    def __add__(self, autre: object) -> "Point2D":
        if not isinstance(autre, Point2D):
            return NotImplemented
        return Point2D(self.x + autre.x, self.y + autre.y)

    def __sub__(self, autre: "Point2D") -> "Point2D":
        return Point2D(self.x - autre.x, self.y - autre.y)

    def fois(self, k: float) -> "Point2D":
        return Point2D(self.x * k, self.y * k)

    def norme(self) -> float:
        return math.hypot(self.x, self.y)


class GeometrieImpossible(ValueError):
    """Les points donnés ne permettent pas de construire l'entité (message pour l'utilisateur)."""


def distance(a: Point2D, b: Point2D) -> float:
    return math.hypot(b.x - a.x, b.y - a.y)


def angle_de(centre: Point2D, point: Point2D) -> float:
    """Angle (radians, entre -π et π) du point vu depuis le centre."""
    return math.atan2(point.y - centre.y, point.x - centre.x)


def balayage(angle_debut: float, angle_fin: float) -> float:
    """Angle parcouru en sens trigonométrique de début à fin, dans ]0, 2π]."""
    ecart = (angle_fin - angle_debut) % (2 * math.pi)
    return ecart if ecart > TOLERANCE else 2 * math.pi


def cercle_trois_points(a: Point2D, b: Point2D, c: Point2D) -> tuple[Point2D, float]:
    """Centre et rayon du cercle passant par trois points (GEO-03, mode trois points)."""
    d = 2 * (a.x * (b.y - c.y) + b.x * (c.y - a.y) + c.x * (a.y - b.y))
    if abs(d) < TOLERANCE:
        raise GeometrieImpossible("Les trois points sont alignés : aucun cercle ne passe par eux.")
    a2, b2, c2 = a.x**2 + a.y**2, b.x**2 + b.y**2, c.x**2 + c.y**2
    centre = Point2D(
        (a2 * (b.y - c.y) + b2 * (c.y - a.y) + c2 * (a.y - b.y)) / d,
        (a2 * (c.x - b.x) + b2 * (a.x - c.x) + c2 * (b.x - a.x)) / d,
    )
    return centre, distance(centre, a)


def sens_trigo(a: Point2D, b: Point2D, c: Point2D) -> bool:
    """Vrai si l'on tourne en sens trigonométrique en allant de a à b puis c."""
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x) > 0


def arc_trois_points(
    debut: Point2D, passage: Point2D, fin: Point2D
) -> tuple[Point2D, Point2D, Point2D]:
    """Arc passant par trois points (GEO-04) : renvoie (centre, début, fin) en sens trigo.

    Les extrémités sont échangées si l'arc va dans le sens des aiguilles d'une montre,
    car un arc est toujours décrit en sens trigonométrique de son début à sa fin.
    """
    centre, _rayon = cercle_trois_points(debut, passage, fin)
    if sens_trigo(debut, passage, fin):
        return centre, debut, fin
    return centre, fin, debut


def arc_tangent(
    depart: Point2D, direction: Point2D, arrivee: Point2D
) -> tuple[Point2D, Point2D, Point2D]:
    """Arc tangent (GEO-04) : part de `depart` dans la `direction` donnée et finit en `arrivee`.

    Utilisé pour enchaîner un arc au bout d'une ligne sans cassure.
    Renvoie (centre, début, fin) en sens trigonométrique.
    """
    longueur = direction.norme()
    if longueur < TOLERANCE:
        raise GeometrieImpossible("Direction de départ nulle.")
    t = direction.fois(1 / longueur)
    normale = Point2D(-t.y, t.x)  # à gauche de la direction
    corde = arrivee - depart
    projection = corde.x * normale.x + corde.y * normale.y
    if abs(projection) < TOLERANCE:
        raise GeometrieImpossible(
            "Le point d'arrivée est dans le prolongement de la ligne : utilisez une ligne."
        )
    # Le centre est sur la normale, à égale distance de départ et d'arrivée.
    rayon_signe = (corde.x**2 + corde.y**2) / (2 * projection)
    centre = depart + normale.fois(rayon_signe)
    if rayon_signe > 0:  # on tourne à gauche : sens trigonométrique
        return centre, depart, arrivee
    return centre, arrivee, depart


def rectangle_deux_coins(a: Point2D, c: Point2D) -> list[Point2D]:
    """Quatre coins (sens trigo) d'un rectangle aligné sur les axes, depuis deux coins opposés."""
    if abs(a.x - c.x) < TOLERANCE or abs(a.y - c.y) < TOLERANCE:
        raise GeometrieImpossible("Rectangle plat : ses deux coins doivent différer en x et en y.")
    x0, x1 = sorted((a.x, c.x))
    y0, y1 = sorted((a.y, c.y))
    return [Point2D(x0, y0), Point2D(x1, y0), Point2D(x1, y1), Point2D(x0, y1)]


def rectangle_centre(centre: Point2D, coin: Point2D) -> list[Point2D]:
    """Rectangle aligné sur les axes, à partir de son centre et d'un coin (GEO-02, mode centré)."""
    oppose = Point2D(2 * centre.x - coin.x, 2 * centre.y - coin.y)
    return rectangle_deux_coins(coin, oppose)


def rectangle_trois_points(a: Point2D, b: Point2D, c: Point2D) -> list[Point2D]:
    """Rectangle incliné (GEO-02, mode trois points) : côté a→b, puis largeur jusqu'à c.

    Renvoie les quatre coins a, b, b + h, a + h, où h est la composante de (c - b)
    perpendiculaire au côté a→b.
    """
    cote = b - a
    longueur = cote.norme()
    if longueur < TOLERANCE:
        raise GeometrieImpossible("Les deux premiers points du rectangle sont confondus.")
    normale = Point2D(-cote.y / longueur, cote.x / longueur)
    hauteur = (c - b).x * normale.x + (c - b).y * normale.y
    if abs(hauteur) < TOLERANCE:
        raise GeometrieImpossible("Le troisième point est sur le premier côté : rectangle plat.")
    h = normale.fois(hauteur)
    coins = [a, b, b + h, a + h]
    return coins if hauteur > 0 else [a + h, b + h, b, a]
