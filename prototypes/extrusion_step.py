"""Prototype 0.3 — extrusion, perçage par opération booléenne, export STEP.

Script jetable : il vérifie qu'on sait enchaîner les opérations de base
d'OpenCascade, comme le fera plus tard une pièce paramétrique.

Pièce : plaque 100 x 50 mm extrudée sur 20 mm, percée d'un trou Ø10
traversant au centre.

Lancement (environnement cao actif) :
    python prototypes/extrusion_step.py

Résultat : prototypes/sortie/plaque_percee.step, à ouvrir dans FreeCAD.
"""

import math
from pathlib import Path

from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakePrism
from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Vec
from OCC.Core.GProp import GProp_GProps
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import (
    STEPControl_AsIs,
    STEPControl_Reader,
    STEPControl_Writer,
)
from OCC.Core.TopoDS import TopoDS_Shape

LONGUEUR = 100.0  # mm
LARGEUR = 50.0  # mm
EPAISSEUR = 20.0  # mm
DIAMETRE_TROU = 10.0  # mm

DOSSIER_SORTIE = Path(__file__).parent / "sortie"


def volume(forme: TopoDS_Shape) -> float:
    """Volume d'un solide en mm³."""
    proprietes = GProp_GProps()
    brepgprop.VolumeProperties(forme, proprietes)
    return proprietes.Mass()


def plaque_extrudee() -> TopoDS_Shape:
    """Esquisse rectangulaire dans le plan XY, extrudée selon Z (bossage extrudé)."""
    contour = BRepBuilderAPI_MakePolygon(
        gp_Pnt(0, 0, 0),
        gp_Pnt(LONGUEUR, 0, 0),
        gp_Pnt(LONGUEUR, LARGEUR, 0),
        gp_Pnt(0, LARGEUR, 0),
        True,  # True = fermer le contour
    ).Wire()
    face = BRepBuilderAPI_MakeFace(contour).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, EPAISSEUR)).Shape()


def percer(piece: TopoDS_Shape) -> TopoDS_Shape:
    """Enlève un cylindre traversant au centre (opération booléenne de soustraction)."""
    centre = gp_Pnt(LONGUEUR / 2, LARGEUR / 2, -1.0)  # démarre 1 mm sous la pièce
    axe = gp_Ax2(centre, gp_Dir(0, 0, 1))
    outil = BRepPrimAPI_MakeCylinder(axe, DIAMETRE_TROU / 2, EPAISSEUR + 2.0).Shape()
    coupe = BRepAlgoAPI_Cut(piece, outil)
    if not coupe.IsDone():
        raise RuntimeError("Le perçage a échoué")
    return coupe.Shape()


def exporter_step(forme: TopoDS_Shape, chemin: Path) -> None:
    ecrivain = STEPControl_Writer()
    ecrivain.Transfer(forme, STEPControl_AsIs)
    if ecrivain.Write(str(chemin)) != IFSelect_RetDone:
        raise RuntimeError(f"Échec de l'écriture de {chemin}")


def relire_step(chemin: Path) -> TopoDS_Shape:
    lecteur = STEPControl_Reader()
    if lecteur.ReadFile(str(chemin)) != IFSelect_RetDone:
        raise RuntimeError(f"Échec de la lecture de {chemin}")
    lecteur.TransferRoots()
    return lecteur.OneShape()


def main() -> None:
    piece = percer(plaque_extrudee())

    theorique = (
        LONGUEUR * LARGEUR * EPAISSEUR - math.pi * (DIAMETRE_TROU / 2) ** 2 * EPAISSEUR
    )
    calcule = volume(piece)

    DOSSIER_SORTIE.mkdir(exist_ok=True)
    chemin = DOSSIER_SORTIE / "plaque_percee.step"
    exporter_step(piece, chemin)
    relu = volume(relire_step(chemin))

    print(f"Volume théorique : {theorique:.2f} mm3")
    print(f"Volume calculé   : {calcule:.2f} mm3")
    print(f"Volume relu STEP : {relu:.2f} mm3")
    print(f"Fichier écrit    : {chemin}")

    ecart = abs(calcule - theorique) / theorique
    ecart_step = abs(relu - calcule) / calcule
    if ecart > 0.001 or ecart_step > 0.001:  # tolérance 0,1 % (recette R3)
        raise SystemExit("ÉCHEC : écart de volume supérieur à 0,1 %")
    print("OK : écarts inférieurs à 0,1 %")


if __name__ == "__main__":
    main()
