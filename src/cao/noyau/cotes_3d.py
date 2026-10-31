"""Dessin des cotes d'une esquisse dans la vue 3D (COT-01, COT-05, COT-06).

Chaque cote devient une « dimension » d'OpenCascade (flèches, lignes d'attache,
texte) posée dans le plan de l'esquisse. Le texte est fourni tout formaté par
l'interface (unité et précision choisies) ; une cote pilotée (de référence) est
écrite entre parenthèses.
Ne dépend pas de Qt.
"""

from collections.abc import Callable

from OCC.Core.AIS import AIS_InteractiveContext, AIS_InteractiveObject
from OCC.Core.gp import gp_Ax2, gp_Ax3, gp_Circ, gp_Dir, gp_Pln, gp_Pnt
from OCC.Core.Graphic3d import Graphic3d_ZLayerId_Topmost
from OCC.Core.Prs3d import (
    Prs3d_DAO_Internal,
    Prs3d_DimensionAspect,
    Prs3d_DTHP_Center,
    Prs3d_DTVP_Above,
)
from OCC.Core.PrsDim import (
    PrsDim_AngleDimension,
    PrsDim_DiameterDimension,
    PrsDim_Dimension,
    PrsDim_LengthDimension,
    PrsDim_RadiusDimension,
)
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB

from cao.esquisse.cotation import points_mesures
from cao.esquisse.esquisse import Arc, Cercle, Cote, Esquisse, GenreCote, Ligne
from cao.esquisse.geometrie import Point2D, distance
from cao.esquisse.plans import PLANS, PlanEsquisse

COULEUR_COTE = (0.10, 0.12, 0.16)
COULEUR_PILOTEE = (0.45, 0.48, 0.55)
HAUTEUR_TEXTE = 17.0  # pixels : texte de taille fixe à l'écran, lisible à tout zoom
LONGUEUR_FLECHE = 2.5  # mm
DEPORT = 8.0  # mm : écart entre la géométrie et la ligne de cote


def _pnt(plan: PlanEsquisse, p: Point2D) -> gp_Pnt:
    return gp_Pnt(*plan.vers_espace(p.x, p.y))


def _pln(plan: PlanEsquisse) -> gp_Pln:
    return gp_Pln(gp_Ax3(gp_Pnt(*plan.origine), gp_Dir(*plan.normale), gp_Dir(*plan.axe_u)))


def _projection(p: Point2D, a: Point2D, b: Point2D) -> Point2D:
    ab = b - a
    t = ((p.x - a.x) * ab.x + (p.y - a.y) * ab.y) / max(ab.x**2 + ab.y**2, 1e-12)
    return a + ab.fois(t)


def _cercle(esquisse: Esquisse, plan: PlanEsquisse, courbe: str) -> tuple[gp_Circ, Point2D]:
    """Cercle porteur et un point du cercle (pour placer la cote de rayon)."""
    entite = esquisse[courbe]
    assert isinstance(entite, Cercle | Arc)
    centre = esquisse.position(entite.centre)
    rayon = esquisse.rayon(courbe)
    repere = gp_Ax2(_pnt(plan, centre), gp_Dir(*plan.normale), gp_Dir(*plan.axe_u))
    if isinstance(entite, Arc):
        a, b = esquisse.position(entite.debut), esquisse.position(entite.fin)
        milieu = Point2D((a.x + b.x) / 2, (a.y + b.y) / 2)
        direction = milieu - centre if distance(milieu, centre) > 1e-9 else a - centre
        sur_arc = centre + direction.fois(rayon / direction.norme())
    else:
        sur_arc = Point2D(centre.x + rayon * 0.7071, centre.y + rayon * 0.7071)
    return gp_Circ(repere, rayon), sur_arc


def _deux_points(esquisse: Esquisse, cote: Cote) -> tuple[Point2D, Point2D]:
    # Mêmes points que le calcul du déport : voir esquisse/cotation.py.
    return points_mesures(esquisse, cote.genre, cote.entites)


def creer_dimension(esquisse: Esquisse, cote: Cote, texte: str) -> AIS_InteractiveObject:
    """Objet OpenCascade dessinant la cote, avec le texte donné."""
    plan = PLANS[esquisse.plan]
    g = cote.genre
    dimension: PrsDim_Dimension
    if g == GenreCote.DIAMETRE:
        cercle, _ = _cercle(esquisse, plan, cote.entites[0])
        dimension = PrsDim_DiameterDimension(cercle, _pln(plan))
    elif g == GenreCote.RAYON:
        cercle, sur_arc = _cercle(esquisse, plan, cote.entites[0])
        dimension = PrsDim_RadiusDimension(cercle, _pnt(plan, sur_arc))
    elif g == GenreCote.ANGLE:
        from cao.esquisse.mesures import intersection

        l1, l2 = (esquisse[e] for e in cote.entites)
        assert isinstance(l1, Ligne) and isinstance(l2, Ligne)
        p1, q1 = esquisse.position(l1.debut), esquisse.position(l1.fin)
        p2, q2 = esquisse.position(l2.debut), esquisse.position(l2.fin)
        sommet = intersection(p1, q1, p2, q2) or p1
        bout1 = q1 if distance(q1, sommet) >= distance(p1, sommet) else p1
        bout2 = q2 if distance(q2, sommet) >= distance(p2, sommet) else p2
        dimension = PrsDim_AngleDimension(_pnt(plan, bout1), _pnt(plan, sommet), _pnt(plan, bout2))
    else:
        a, b = _deux_points(esquisse, cote)
        longueur = PrsDim_LengthDimension(_pnt(plan, a), _pnt(plan, b), _pln(plan))
        if g == GenreCote.HORIZONTALE:
            longueur.SetDirection(gp_Dir(*plan.axe_u))
        elif g == GenreCote.VERTICALE:
            longueur.SetDirection(gp_Dir(*plan.axe_v))
        longueur.SetFlyout(cote.deport)
        dimension = longueur
    dimension.SetCustomValue(texte)
    aspect = Prs3d_DimensionAspect()  # la cote n'a pas d'aspect avant son 1er affichage
    r, v, b_ = COULEUR_PILOTEE if cote.pilotee else COULEUR_COTE
    aspect.SetCommonColor(Quantity_Color(r, v, b_, Quantity_TOC_RGB))
    aspect.TextAspect().SetHeight(HAUTEUR_TEXTE)
    aspect.TextAspect().Aspect().SetFont("Arial")  # police nette, présente sous Windows et Linux
    # Texte au milieu, au-dessus de la ligne de cote, flèches vers l'intérieur (dessin technique).
    aspect.SetTextHorizontalPosition(Prs3d_DTHP_Center)
    aspect.SetTextVerticalPosition(Prs3d_DTVP_Above)
    aspect.SetArrowOrientation(Prs3d_DAO_Internal)
    aspect.ArrowAspect().SetLength(LONGUEUR_FLECHE)
    dimension.SetDimensionAspect(aspect)
    dimension.SetZLayer(Graphic3d_ZLayerId_Topmost)
    return dimension


def afficher_cotes(
    contexte: AIS_InteractiveContext,
    esquisse: Esquisse,
    texte_de: Callable[[Cote], str],
    presentations: dict[str, AIS_InteractiveObject],
) -> None:
    """(Ré)affiche toutes les cotes de l'esquisse ; clé « cote:D1 » dans `presentations`."""
    for cle in [c for c in presentations if c.startswith("cote:")]:
        contexte.Remove(presentations.pop(cle), False)
    for cote in esquisse.cotes.values():
        try:
            dimension = creer_dimension(esquisse, cote, texte_de(cote))
        except Exception:
            continue
        contexte.Display(dimension, False)
        presentations[f"cote:{cote.id}"] = dimension
