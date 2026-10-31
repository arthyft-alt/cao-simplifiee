"""Cotation intelligente (tableau 3.5 du cahier des charges) : un seul outil « Cote »,
le type de cote est déduit des entités sélectionnées et de la position du curseur.

    une ligne                  longueur ; horizontale ou verticale si le curseur est
                               placé au-dessus/au-dessous ou à gauche/à droite d'une
                               ligne inclinée (comme SolidWorks)
    deux points                distance (même règle du curseur)
    un point et une ligne      distance
    deux lignes parallèles     distance entre elles
    deux lignes sécantes       angle
    un cercle                  diamètre
    un arc                     rayon
    cercle/arc + ligne         distance du centre à la ligne
    deux cercles/arcs          distance entre les centres
Aucune dépendance à Qt ou OpenCascade.
"""

from cao.esquisse.esquisse import Arc, Cercle, CoteImpossible, Esquisse, GenreCote, Ligne
from cao.esquisse.geometrie import TOLERANCE, Point2D
from cao.esquisse.mesures import lignes_paralleles

MESSAGE_SELECTION = (
    "Cotation : sélectionnez une ligne, un cercle ou un arc, ou deux entités "
    "(points, lignes, cercles), puis cliquez dans le vide pour placer la cote."
)


def _centre(esquisse: Esquisse, courbe: str) -> str:
    entite = esquisse[courbe]
    assert isinstance(entite, Cercle | Arc)
    return entite.centre


def _selon_curseur(a: Point2D, b: Point2D, curseur: Point2D | None) -> GenreCote:
    """Longueur alignée, horizontale ou verticale entre deux points, selon le curseur."""
    if curseur is None or abs(a.x - b.x) < TOLERANCE or abs(a.y - b.y) < TOLERANCE:
        return GenreCote.LONGUEUR  # segment horizontal ou vertical : sa longueur suffit
    dans_x = min(a.x, b.x) <= curseur.x <= max(a.x, b.x)
    dans_y = min(a.y, b.y) <= curseur.y <= max(a.y, b.y)
    if dans_x and not dans_y:
        return GenreCote.HORIZONTALE  # curseur au-dessus ou au-dessous : écart en x
    if dans_y and not dans_x:
        return GenreCote.VERTICALE  # curseur à gauche ou à droite : écart en y
    return GenreCote.LONGUEUR


def deduire_cote(
    esquisse: Esquisse, selection: list[str], curseur: Point2D | None = None
) -> tuple[GenreCote, list[str]]:
    """Type de cote et entités à coter ; CoteImpossible si la sélection ne convient pas."""
    genres = sorted(esquisse.genre_entite(e) for e in selection)
    if genres == ["ligne"]:
        ligne = esquisse[selection[0]]
        assert isinstance(ligne, Ligne)
        a, b = esquisse.position(ligne.debut), esquisse.position(ligne.fin)
        return _selon_curseur(a, b, curseur), list(selection)
    if genres == ["courbe"]:
        courbe = esquisse[selection[0]]
        genre = GenreCote.DIAMETRE if isinstance(courbe, Cercle) else GenreCote.RAYON
        return genre, list(selection)
    if genres == ["point", "point"]:
        a, b = (esquisse.position(e) for e in selection)
        return _selon_curseur(a, b, curseur), list(selection)
    if genres == ["ligne", "point"]:
        return GenreCote.DISTANCE, list(selection)
    if genres == ["ligne", "ligne"]:
        if lignes_paralleles(esquisse, selection[0], selection[1]):
            return GenreCote.DISTANCE, list(selection)
        return GenreCote.ANGLE, list(selection)
    if genres == ["courbe", "ligne"]:
        id_courbe = next(e for e in selection if esquisse.genre_entite(e) == "courbe")
        id_ligne = next(e for e in selection if esquisse.genre_entite(e) == "ligne")
        return GenreCote.DISTANCE, [_centre(esquisse, id_courbe), id_ligne]
    if genres == ["courbe", "courbe"]:
        centres = [_centre(esquisse, e) for e in selection]
        if centres[0] == centres[1]:
            raise CoteImpossible("Ces deux cercles ont le même centre : cotez leurs diamètres.")
        a, b = (esquisse.position(c) for c in centres)
        return _selon_curseur(a, b, curseur), centres
    if genres == ["courbe", "point"]:
        id_courbe = next(e for e in selection if esquisse.genre_entite(e) == "courbe")
        point = next(e for e in selection if esquisse.genre_entite(e) == "point")
        centre = _centre(esquisse, id_courbe)
        a, b = esquisse.position(centre), esquisse.position(point)
        return _selon_curseur(a, b, curseur), [centre, point]
    raise CoteImpossible(MESSAGE_SELECTION)


DEPORT_MINIMUM = 3.0  # mm : en dessous, la cote serait collée à la géométrie


def _pied(p: Point2D, a: Point2D, b: Point2D) -> Point2D:
    """Pied de la perpendiculaire abaissée de p sur la droite (a, b)."""
    ab = b - a
    t = ((p.x - a.x) * ab.x + (p.y - a.y) * ab.y) / max(ab.x**2 + ab.y**2, 1e-12)
    return a + ab.fois(t)


def points_mesures(
    esquisse: Esquisse, genre: GenreCote, entites: list[str]
) -> tuple[Point2D, Point2D]:
    """Les deux points entre lesquels une cote de longueur est dessinée.

    Partagée par le calcul du déport et par le dessin de la cote (noyau/cotes_3d.py) :
    les deux doivent raisonner sur les mêmes points (régressions signalées par Simon).
        une ligne                 ses extrémités
        distance point - ligne    le point et son pied sur la ligne
        distance ligne - ligne    le début de la 1re ligne et son pied sur la 2e
        deux points               ces deux points
    """
    if len(entites) == 1:
        ligne = esquisse[entites[0]]
        assert isinstance(ligne, Ligne)
        return esquisse.position(ligne.debut), esquisse.position(ligne.fin)
    if genre == GenreCote.DISTANCE:
        source = esquisse[entites[0]]
        cible = esquisse[entites[1]]
        assert isinstance(cible, Ligne)
        p = esquisse.position(source.debut if isinstance(source, Ligne) else entites[0])
        return p, _pied(p, esquisse.position(cible.debut), esquisse.position(cible.fin))
    return esquisse.position(entites[0]), esquisse.position(entites[1])


def deport_pour(
    esquisse: Esquisse, genre: GenreCote, entites: list[str], curseur: Point2D
) -> float:
    """Écart signé de la ligne de cote, pour qu'elle passe là où se trouve la souris.

    Conventions d'OpenCascade (vérifiées à l'écran le 2026-10-31) :
        cote alignée (longueur, distance) : écart perpendiculaire au segment mesuré
            a -> b, positif à gauche de ce segment ;
        cote horizontale / verticale : écart depuis le 2e point, positif vers le haut
            (horizontale) ou vers la gauche (verticale), quel que soit le sens de tracé.
    """
    if genre in (GenreCote.RAYON, GenreCote.DIAMETRE, GenreCote.ANGLE):
        return 8.0
    a, b = points_mesures(esquisse, genre, entites)
    if genre == GenreCote.HORIZONTALE:
        return _au_moins(curseur.y - b.y)
    if genre == GenreCote.VERTICALE:
        return _au_moins(b.x - curseur.x)
    direction = b - a
    longueur = direction.norme()
    if longueur < TOLERANCE:
        return 8.0
    # Produit vectoriel : positif si le curseur est à gauche du segment a -> b.
    return _au_moins((direction.x * (curseur.y - a.y) - direction.y * (curseur.x - a.x)) / longueur)


def _au_moins(ecart: float) -> float:
    """Écart d'au moins DEPORT_MINIMUM, en gardant son signe."""
    if abs(ecart) < DEPORT_MINIMUM:
        return DEPORT_MINIMUM if ecart >= 0 else -DEPORT_MINIMUM
    return ecart
