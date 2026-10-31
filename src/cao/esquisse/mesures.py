"""Mesures actuelles de la géométrie d'une esquisse : valeur d'une cote, parallélisme.

Sert à donner sa valeur de départ à une nouvelle cote et à mettre à jour les
cotes pilotées (de référence) après chaque résolution.
"""

import math

from cao.esquisse.esquisse import Cote, Esquisse, GenreCote, Ligne
from cao.esquisse.geometrie import Point2D, distance

TOLERANCE_ANGLE = 1e-6  # radians


def _direction(esquisse: Esquisse, ligne: str) -> Point2D:
    entite = esquisse[ligne]
    assert isinstance(entite, Ligne)
    return esquisse.position(entite.fin) - esquisse.position(entite.debut)


def _extremites(esquisse: Esquisse, cote: Cote) -> tuple[Point2D, Point2D]:
    """Les deux points concernés par une cote de longueur, horizontale ou verticale."""
    if len(cote.entites) == 1:
        entite = esquisse[cote.entites[0]]
        assert isinstance(entite, Ligne)
        return esquisse.position(entite.debut), esquisse.position(entite.fin)
    return esquisse.position(cote.entites[0]), esquisse.position(cote.entites[1])


def _intersection(a: Point2D, b: Point2D, c: Point2D, d: Point2D) -> Point2D | None:
    """Point de rencontre des droites (a, b) et (c, d), ou None si elles sont parallèles."""
    r, s = b - a, d - c
    denominateur = r.x * s.y - r.y * s.x
    if abs(denominateur) < 1e-12:
        return None
    t = ((c.x - a.x) * s.y - (c.y - a.y) * s.x) / denominateur
    return a + r.fois(t)


def angle_interieur(esquisse: Esquisse, l1: str, l2: str) -> tuple[float, bool]:
    """Angle (degrés) que l'on voit entre deux lignes, à l'intérieur du « V » qu'elles forment.

    Chaque ligne est vue depuis le point de rencontre des deux droites, vers son
    extrémité la plus éloignée. Renvoie aussi `meme_sens` : True si ces deux
    directions sont les sens de tracé des lignes (ou tous deux les sens inverses),
    ce qui permet de traduire l'angle pour le solveur, qui raisonne sur les sens
    de tracé.
    """
    a, b = esquisse[l1], esquisse[l2]
    assert isinstance(a, Ligne) and isinstance(b, Ligne)
    pa, qa = esquisse.position(a.debut), esquisse.position(a.fin)
    pb, qb = esquisse.position(b.debut), esquisse.position(b.fin)
    rencontre = _intersection(pa, qa, pb, qb)
    if rencontre is None:
        raise ValueError("lignes parallèles : pas d'angle")
    # Pour chaque ligne : +1 si l'on va dans son sens de tracé en partant de la rencontre.
    sens_a = 1 if distance(qa, rencontre) >= distance(pa, rencontre) else -1
    sens_b = 1 if distance(qb, rencontre) >= distance(pb, rencontre) else -1
    va = (qa - pa).fois(sens_a)
    vb = (qb - pb).fois(sens_b)
    cosinus = (va.x * vb.x + va.y * vb.y) / (va.norme() * vb.norme())
    return math.degrees(math.acos(max(-1.0, min(1.0, cosinus)))), sens_a == sens_b


def lignes_paralleles(esquisse: Esquisse, l1: str, l2: str) -> bool:
    a, b = _direction(esquisse, l1), _direction(esquisse, l2)
    sinus = abs(a.x * b.y - a.y * b.x) / (a.norme() * b.norme())
    return sinus < 1e-3  # à moins de 0,06° près : tracé à la main presque parallèle


def distance_point_droite(p: Point2D, a: Point2D, b: Point2D) -> float:
    ab = b - a
    return abs(ab.x * (p.y - a.y) - ab.y * (p.x - a.x)) / ab.norme()


def mesurer_cote(esquisse: Esquisse, cote: Cote) -> float:
    """Valeur que prendrait la cote sur la géométrie actuelle."""
    g = cote.genre
    if g in (GenreCote.LONGUEUR, GenreCote.HORIZONTALE, GenreCote.VERTICALE):
        a, b = _extremites(esquisse, cote)
        if g == GenreCote.HORIZONTALE:
            return abs(b.x - a.x)
        if g == GenreCote.VERTICALE:
            return abs(b.y - a.y)
        return distance(a, b)
    if g == GenreCote.DISTANCE:
        premiere = cote.entites[0]
        seconde = esquisse[cote.entites[1]]
        assert isinstance(seconde, Ligne)
        a, b = esquisse.position(seconde.debut), esquisse.position(seconde.fin)
        if esquisse.genre_entite(premiere) == "point":
            return distance_point_droite(esquisse.position(premiere), a, b)
        autre = esquisse[premiere]
        assert isinstance(autre, Ligne)
        return distance_point_droite(esquisse.position(autre.debut), a, b)
    if g == GenreCote.ANGLE:
        return angle_interieur(esquisse, cote.entites[0], cote.entites[1])[0]
    rayon = esquisse.rayon(cote.entites[0])
    return rayon if g == GenreCote.RAYON else 2 * rayon
