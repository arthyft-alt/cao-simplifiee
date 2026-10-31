"""Affichage des esquisses dans la vue 3D et conversion des clics en coordonnées du plan.

Chaque entité de l'esquisse devient une arête (ligne, cercle, arc) ou un sommet
(point) d'OpenCascade, posé sur son plan dans l'espace. Couleurs (ESQ-07) :
    bleu  : esquisse sous-contrainte
    noir  : totalement contrainte
    rouge : sur-contrainte (relations en conflit)
    gris  : esquisse qui n'est pas en cours d'édition
Les entités de construction sont en traits interrompus (ESQ-08).
Ne dépend pas de Qt.
"""

from dataclasses import dataclass, field
from enum import Enum

from OCC.Core.AIS import AIS_InteractiveContext, AIS_Shape
from OCC.Core.Aspect import (
    Aspect_TOL_DASH,
    Aspect_TOL_SOLID,
    Aspect_TOM_O_POINT,
    Aspect_TOM_PLUS,
    Aspect_TOM_RING1,
)
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeVertex
from OCC.Core.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt
from OCC.Core.Graphic3d import Graphic3d_ZLayerId_Topmost
from OCC.Core.Prs3d import Prs3d_LineAspect, Prs3d_PointAspect
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.V3d import V3d_View

from cao.esquisse.aimants import Aimantation
from cao.esquisse.esquisse import ORIGINE, Arc, Cercle, Esquisse, Ligne, Point
from cao.esquisse.geometrie import Point2D
from cao.esquisse.outils import Apercu
from cao.esquisse.plans import PLANS, PlanEsquisse


class Teinte(Enum):
    SOUS_CONTRAINTE = (0.10, 0.35, 0.85)  # bleu
    TOTALEMENT_CONTRAINTE = (0.05, 0.05, 0.05)  # noir
    SUR_CONTRAINTE = (0.85, 0.10, 0.10)  # rouge
    INACTIVE = (0.45, 0.48, 0.55)  # gris : esquisse fermée
    APERCU = (0.45, 0.45, 0.45)  # tracé provisoire
    ORIGINE = (0.80, 0.15, 0.15)  # rouge, comme l'origine de SolidWorks
    AIMANT = (0.95, 0.55, 0.05)  # orange : guides et point attrapé


EPAISSEUR = 2.0


def _couleur(teinte: Teinte) -> Quantity_Color:
    r, v, b = teinte.value
    return Quantity_Color(r, v, b, Quantity_TOC_RGB)


def _pnt(plan: PlanEsquisse, p: Point2D) -> gp_Pnt:
    return gp_Pnt(*plan.vers_espace(p.x, p.y))


def _repere(plan: PlanEsquisse, centre: Point2D) -> gp_Ax2:
    return gp_Ax2(_pnt(plan, centre), gp_Dir(*plan.normale), gp_Dir(*plan.axe_u))


def arete_ligne(plan: PlanEsquisse, a: Point2D, b: Point2D) -> TopoDS_Shape:
    return BRepBuilderAPI_MakeEdge(_pnt(plan, a), _pnt(plan, b)).Edge()


def arete_cercle(plan: PlanEsquisse, centre: Point2D, rayon: float) -> TopoDS_Shape:
    return BRepBuilderAPI_MakeEdge(gp_Circ(_repere(plan, centre), rayon)).Edge()


def arete_arc(plan: PlanEsquisse, centre: Point2D, debut: Point2D, fin: Point2D) -> TopoDS_Shape:
    """Arc en sens trigonométrique dans le plan (u, v), donc sens direct autour de la normale."""
    rayon = ((debut.x - centre.x) ** 2 + (debut.y - centre.y) ** 2) ** 0.5
    cercle = gp_Circ(_repere(plan, centre), rayon)
    return BRepBuilderAPI_MakeEdge(cercle, _pnt(plan, debut), _pnt(plan, fin)).Edge()


def formes_esquisse(esquisse: Esquisse) -> dict[str, tuple[TopoDS_Shape, bool]]:
    """Forme 3D de chaque entité : identifiant -> (forme, construction)."""
    plan = PLANS[esquisse.plan]
    formes: dict[str, tuple[TopoDS_Shape, bool]] = {}
    for entite in esquisse.entites.values():
        if isinstance(entite, Point):
            sommet = BRepBuilderAPI_MakeVertex(_pnt(plan, Point2D(entite.x, entite.y))).Vertex()
            formes[entite.id] = (sommet, entite.construction)
        elif isinstance(entite, Ligne):
            a, b = esquisse.position(entite.debut), esquisse.position(entite.fin)
            formes[entite.id] = (arete_ligne(plan, a, b), entite.construction)
        elif isinstance(entite, Cercle):
            centre = esquisse.position(entite.centre)
            formes[entite.id] = (arete_cercle(plan, centre, entite.rayon), entite.construction)
        elif isinstance(entite, Arc):
            arete = arete_arc(
                plan,
                esquisse.position(entite.centre),
                esquisse.position(entite.debut),
                esquisse.position(entite.fin),
            )
            formes[entite.id] = (arete, entite.construction)
    return formes


def _style(presentation: AIS_Shape, teinte: Teinte, construction: bool) -> None:
    couleur = _couleur(teinte)
    presentation.SetColor(couleur)
    attributs = presentation.Attributes()
    type_trait = Aspect_TOL_DASH if construction else Aspect_TOL_SOLID
    attributs.SetWireAspect(Prs3d_LineAspect(couleur, type_trait, EPAISSEUR))
    attributs.SetLineAspect(Prs3d_LineAspect(couleur, type_trait, EPAISSEUR))
    attributs.SetPointAspect(Prs3d_PointAspect(Aspect_TOM_O_POINT, couleur, 1.6))
    presentation.SetZLayer(Graphic3d_ZLayerId_Topmost)  # l'esquisse reste visible devant le volume


@dataclass
class AffichageEsquisse:
    """Objets affichés pour une esquisse, pour pouvoir les retirer ou retrouver l'entité cliquée."""

    presentations: dict[str, AIS_Shape] = field(default_factory=dict)

    def retirer(self, contexte: AIS_InteractiveContext) -> None:
        for presentation in self.presentations.values():
            contexte.Remove(presentation, False)
        self.presentations.clear()

    def entite_de(self, forme: TopoDS_Shape) -> str | None:
        """Identifiant de l'entité dont la forme a été cliquée."""
        for identifiant, presentation in self.presentations.items():
            if presentation.Shape().IsSame(forme):
                return identifiant
        return None


def afficher_esquisse(
    contexte: AIS_InteractiveContext,
    esquisse: Esquisse,
    teinte: Teinte,
    avec_points: bool,
    affichage: AffichageEsquisse | None = None,
) -> AffichageEsquisse:
    """(Ré)affiche une esquisse ; les points ne sont montrés que pendant l'édition."""
    affichage = affichage or AffichageEsquisse()
    affichage.retirer(contexte)
    for identifiant, (forme, construction) in formes_esquisse(esquisse).items():
        est_point = identifiant.startswith("P")
        if est_point and not avec_points:
            continue
        presentation = AIS_Shape(forme)
        _style(presentation, teinte, construction)
        contexte.Display(presentation, False)
        affichage.presentations[identifiant] = presentation
    if avec_points:  # origine du plan : repère rouge, sur lequel on peut s'accrocher
        origine = AIS_Shape(
            BRepBuilderAPI_MakeVertex(_pnt(PLANS[esquisse.plan], Point2D(0, 0))).Vertex()
        )
        _style(origine, Teinte.ORIGINE, False)
        origine.Attributes().SetPointAspect(
            Prs3d_PointAspect(Aspect_TOM_PLUS, _couleur(Teinte.ORIGINE), 3.0)
        )
        contexte.Display(origine, False)
        affichage.presentations[ORIGINE] = origine
    contexte.UpdateCurrentViewer()
    return affichage


def afficher_apercu(
    contexte: AIS_InteractiveContext,
    plan: PlanEsquisse,
    apercu: Apercu,
    affichage: AffichageEsquisse | None = None,
) -> AffichageEsquisse:
    """Tracé provisoire en pointillés gris (non sélectionnable)."""
    affichage = affichage or AffichageEsquisse()
    affichage.retirer(contexte)
    aretes = [arete_ligne(plan, a, b) for a, b in apercu.lignes if a != b]
    aretes += [arete_cercle(plan, c, r) for c, r in apercu.cercles]
    aretes += [arete_arc(plan, c, d, f) for c, d, f in apercu.arcs]
    for i, arete in enumerate(aretes):
        presentation = AIS_Shape(arete)
        _style(presentation, Teinte.APERCU, construction=True)
        contexte.Display(presentation, 0, -1, False)  # mode 0, aucune sélection
        affichage.presentations[f"apercu{i}"] = presentation
    contexte.UpdateCurrentViewer()
    return affichage


def afficher_aimant(
    contexte: AIS_InteractiveContext,
    plan: PlanEsquisse,
    aimantation: Aimantation,
    affichage: AffichageEsquisse | None = None,
) -> AffichageEsquisse:
    """Guides orange en pointillés et rond orange sur le point attrapé (ESQ-04)."""
    affichage = affichage or AffichageEsquisse()
    affichage.retirer(contexte)
    for i, (a, b) in enumerate(aimantation.guides):
        if a == b:
            continue
        guide = AIS_Shape(arete_ligne(plan, a, b))
        _style(guide, Teinte.AIMANT, construction=True)
        contexte.Display(guide, 0, -1, False)
        affichage.presentations[f"guide{i}"] = guide
    if aimantation.active:
        sommet = BRepBuilderAPI_MakeVertex(_pnt(plan, aimantation.position)).Vertex()
        repere = AIS_Shape(sommet)
        _style(repere, Teinte.AIMANT, construction=False)
        repere.Attributes().SetPointAspect(
            Prs3d_PointAspect(Aspect_TOM_RING1, _couleur(Teinte.AIMANT), 2.5)
        )
        contexte.Display(repere, 0, -1, False)
        affichage.presentations["repere"] = repere
    contexte.UpdateCurrentViewer()
    return affichage


def point_sur_plan(vue: V3d_View, x: int, y: int, plan: PlanEsquisse) -> Point2D | None:
    """Coordonnées (u, v) du point du plan d'esquisse sous le pixel (x, y), ou None
    si le regard est parallèle au plan."""
    px, py, pz, dx, dy, dz = vue.ConvertWithProj(x, y)
    nx, ny, nz = plan.normale
    ox, oy, oz = plan.origine
    denominateur = dx * nx + dy * ny + dz * nz
    if abs(denominateur) < 1e-9:
        return None
    t = ((ox - px) * nx + (oy - py) * ny + (oz - pz) * nz) / denominateur
    u, v = plan.vers_plan((px + t * dx, py + t * dy, pz + t * dz))
    return Point2D(u, v)


def taille_pixel(vue: V3d_View) -> float:
    """Taille d'un pixel de l'écran, en mm, dans la vue actuelle (pour l'accrochage)."""
    return float(vue.Convert(100)) / 100.0
