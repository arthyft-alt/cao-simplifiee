"""Entité de l'esquisse la plus proche du curseur, pour la sélection à la souris.

Plus fiable que la détection d'OpenCascade pour de petits points : on calcule
directement, dans le plan, la distance du curseur à chaque entité.
Priorité aux points (origine comprise), puis aux courbes. Sans dépendance.
"""

import math

from cao.esquisse.esquisse import ORIGINE, Arc, Cercle, Esquisse, Ligne
from cao.esquisse.geometrie import Point2D, angle_de, balayage, distance


def distance_segment(p: Point2D, a: Point2D, b: Point2D) -> float:
    ab = b - a
    longueur2 = ab.x**2 + ab.y**2
    if longueur2 == 0:
        return distance(p, a)
    t = max(0.0, min(1.0, ((p.x - a.x) * ab.x + (p.y - a.y) * ab.y) / longueur2))
    return distance(p, a + ab.fois(t))


def distance_courbe(esquisse: Esquisse, identifiant: str, p: Point2D) -> float:
    entite = esquisse[identifiant]
    if isinstance(entite, Ligne):
        return distance_segment(p, esquisse.position(entite.debut), esquisse.position(entite.fin))
    if isinstance(entite, Cercle):
        return abs(distance(p, esquisse.position(entite.centre)) - entite.rayon)
    if isinstance(entite, Arc):
        centre = esquisse.position(entite.centre)
        debut, fin = esquisse.position(entite.debut), esquisse.position(entite.fin)
        ouverture = balayage(angle_de(centre, debut), angle_de(centre, fin))
        position = balayage(angle_de(centre, debut), angle_de(centre, p)) % (2 * math.pi)
        if position <= ouverture:  # le curseur est en face de l'arc
            return abs(distance(p, centre) - esquisse.rayon(identifiant))
        return min(distance(p, debut), distance(p, fin))
    return math.inf


def entite_proche(esquisse: Esquisse, position: Point2D, tolerance: float) -> str | None:
    """Identifiant du point (prioritaire) ou de la courbe à moins de `tolerance` mm, ou None."""
    points = [p.id for p in esquisse.points()] + [ORIGINE]
    proche = min(points, key=lambda i: distance(esquisse.position(i), position))
    if distance(esquisse.position(proche), position) <= tolerance:
        return proche
    courbes = [c.id for c in esquisse.courbes()]
    if not courbes:
        return None
    meilleure = min(courbes, key=lambda i: distance_courbe(esquisse, i, position))
    return meilleure if distance_courbe(esquisse, meilleure, position) <= tolerance else None
