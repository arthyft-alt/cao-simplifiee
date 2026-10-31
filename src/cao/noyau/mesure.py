"""Mesure rapide entre entités sélectionnées (exigence IHM-12).

Selon ce qui est sélectionné :
    1 arête   -> longueur ; rayon et diamètre si c'est un cercle ou un arc
    1 face    -> aire ; rayon et diamètre si c'est un cylindre
    1 sommet  -> coordonnées X, Y, Z
    2 entités -> distance minimale ; écarts dX dY dZ entre deux sommets ;
                 angle entre deux arêtes droites ou deux faces planes
Ce module ne dépend pas de Qt : il renvoie des résultats chiffrés, que
l'interface met en forme.
"""

import math
from dataclasses import dataclass
from enum import Enum

from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GeomAbs import GeomAbs_Circle, GeomAbs_Cylinder, GeomAbs_Line, GeomAbs_Plane
from OCC.Core.gp import gp_Dir
from OCC.Core.GProp import GProp_GProps
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_REVERSED, TopAbs_VERTEX
from OCC.Core.TopoDS import TopoDS_Shape, topods

# Nom à utiliser hors du noyau pour désigner une forme (face, arête, sommet, solide),
# sans importer OpenCascade (règle d'architecture).
Forme = TopoDS_Shape


class Unite(Enum):
    LONGUEUR = "mm"
    AIRE = "mm²"
    ANGLE = "°"


@dataclass(frozen=True)
class Valeur:
    nom: str  # ex. « Longueur »
    valeur: float
    unite: Unite


def _longueur(arete: TopoDS_Shape) -> float:
    proprietes = GProp_GProps()
    brepgprop.LinearProperties(arete, proprietes)
    return float(proprietes.Mass())


def _aire(face: TopoDS_Shape) -> float:
    proprietes = GProp_GProps()
    brepgprop.SurfaceProperties(face, proprietes)
    return float(proprietes.Mass())


def direction_droite(arete: TopoDS_Shape) -> gp_Dir | None:
    """Direction d'une arête droite, ou None si elle n'est pas droite."""
    courbe = BRepAdaptor_Curve(topods.Edge(arete))
    if courbe.GetType() != GeomAbs_Line:
        return None
    return courbe.Line().Direction()


def normale_plane(face: TopoDS_Shape) -> gp_Dir | None:
    """Normale sortante d'une face plane, ou None si elle n'est pas plane."""
    surface = BRepAdaptor_Surface(topods.Face(face))
    if surface.GetType() != GeomAbs_Plane:
        return None
    normale = surface.Plane().Axis().Direction()
    if face.Orientation() == TopAbs_REVERSED:
        normale.Reverse()
    return normale


def premiere_normale_plane(formes: list[TopoDS_Shape]) -> gp_Dir | None:
    """Normale de la première face plane de la liste (pour « Normale à »)."""
    for forme in formes:
        if forme.ShapeType() == TopAbs_FACE:
            normale = normale_plane(forme)
            if normale is not None:
                return normale
    return None


def _angle_entre_directions(d1: gp_Dir, d2: gp_Dir) -> float:
    """Angle entre deux directions, ramené entre 0 et 90° (le sens ne compte pas)."""
    angle = math.degrees(d1.Angle(d2))
    return min(angle, 180.0 - angle)


def _mesurer_une(forme: TopoDS_Shape) -> list[Valeur]:
    genre = forme.ShapeType()
    if genre == TopAbs_EDGE:
        valeurs = [Valeur("Longueur", _longueur(forme), Unite.LONGUEUR)]
        courbe = BRepAdaptor_Curve(topods.Edge(forme))
        if courbe.GetType() == GeomAbs_Circle:
            rayon = courbe.Circle().Radius()
            valeurs += [
                Valeur("Rayon", rayon, Unite.LONGUEUR),
                Valeur("Diamètre", 2 * rayon, Unite.LONGUEUR),
            ]
        return valeurs
    if genre == TopAbs_FACE:
        valeurs = [Valeur("Aire", _aire(forme), Unite.AIRE)]
        surface = BRepAdaptor_Surface(topods.Face(forme))
        if surface.GetType() == GeomAbs_Cylinder:
            rayon = surface.Cylinder().Radius()
            valeurs += [
                Valeur("Rayon", rayon, Unite.LONGUEUR),
                Valeur("Diamètre", 2 * rayon, Unite.LONGUEUR),
            ]
        return valeurs
    if genre == TopAbs_VERTEX:
        point = BRep_Tool.Pnt(topods.Vertex(forme))
        return [
            Valeur("X", point.X(), Unite.LONGUEUR),
            Valeur("Y", point.Y(), Unite.LONGUEUR),
            Valeur("Z", point.Z(), Unite.LONGUEUR),
        ]
    return []


def _mesurer_deux(a: TopoDS_Shape, b: TopoDS_Shape) -> list[Valeur]:
    calcul = BRepExtrema_DistShapeShape(a, b)
    valeurs = [Valeur("Distance", calcul.Value(), Unite.LONGUEUR)]

    if a.ShapeType() == TopAbs_VERTEX and b.ShapeType() == TopAbs_VERTEX:
        p, q = BRep_Tool.Pnt(topods.Vertex(a)), BRep_Tool.Pnt(topods.Vertex(b))
        valeurs += [
            Valeur("dX", abs(q.X() - p.X()), Unite.LONGUEUR),
            Valeur("dY", abs(q.Y() - p.Y()), Unite.LONGUEUR),
            Valeur("dZ", abs(q.Z() - p.Z()), Unite.LONGUEUR),
        ]

    directions: list[gp_Dir | None] = []
    for forme in (a, b):
        if forme.ShapeType() == TopAbs_EDGE:
            directions.append(direction_droite(forme))
        elif forme.ShapeType() == TopAbs_FACE:
            directions.append(normale_plane(forme))
        else:
            directions.append(None)
    d1, d2 = directions
    if d1 is not None and d2 is not None and a.ShapeType() == b.ShapeType():
        valeurs.append(Valeur("Angle", _angle_entre_directions(d1, d2), Unite.ANGLE))
    return valeurs


def mesurer(formes: list[TopoDS_Shape]) -> list[Valeur]:
    """Mesures pertinentes pour la sélection (liste vide si rien à mesurer)."""
    if len(formes) == 1:
        return _mesurer_une(formes[0])
    if len(formes) == 2:
        return _mesurer_deux(formes[0], formes[1])
    return []


def formater(valeur: Valeur, decimales: int = 2) -> str:
    """« Longueur : 100,00 mm » — virgule décimale, à la française."""
    nombre = f"{valeur.valeur:.{decimales}f}".replace(".", ",")
    espace = "" if valeur.unite == Unite.ANGLE else " "
    return f"{valeur.nom} : {nombre}{espace}{valeur.unite.value}"
