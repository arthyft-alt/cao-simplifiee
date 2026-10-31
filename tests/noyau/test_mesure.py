"""Tests IHM-12 : mesure rapide sur une boîte de 100 × 50 × 20 mm percée d'un trou Ø10.

Critère de l'étape 1.4 (plan de développement) : la mesure d'une arête de la
boîte est exacte.
"""

import math

import pytest
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Shape, topods

from cao.noyau.mesure import Unite, Valeur, formater, mesurer, normale_plane


def sous_formes(forme: TopoDS_Shape, genre: int) -> list[TopoDS_Shape]:
    resultat = []
    explorateur = TopExp_Explorer(forme, genre)
    while explorateur.More():
        resultat.append(explorateur.Current())
        explorateur.Next()
    return resultat


@pytest.fixture(scope="module")
def boite() -> TopoDS_Shape:
    return BRepPrimAPI_MakeBox(100.0, 50.0, 20.0).Shape()


@pytest.fixture(scope="module")
def boite_percee(boite: TopoDS_Shape) -> TopoDS_Shape:
    outil = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(50, 25, -1), gp_Dir(0, 0, 1)), 5.0, 22.0).Shape()
    return BRepAlgoAPI_Cut(boite, outil).Shape()


def valeurs(resultats: list[Valeur]) -> dict[str, float]:
    return {v.nom: v.valeur for v in resultats}


def test_longueurs_des_aretes_de_la_boite(boite: TopoDS_Shape) -> None:
    longueurs = sorted(
        {round(valeurs(mesurer([a]))["Longueur"], 9) for a in sous_formes(boite, TopAbs_EDGE)}
    )
    assert longueurs == [20.0, 50.0, 100.0]


def test_aire_d_une_face(boite: TopoDS_Shape) -> None:
    aires = sorted(
        {round(valeurs(mesurer([f]))["Aire"], 6) for f in sous_formes(boite, TopAbs_FACE)}
    )
    assert aires == [1000.0, 2000.0, 5000.0]


def test_coordonnees_d_un_sommet(boite: TopoDS_Shape) -> None:
    sommet = next(
        s
        for s in sous_formes(boite, TopAbs_VERTEX)
        if BRep_Tool.Pnt(topods.Vertex(s)).Distance(gp_Pnt(100, 50, 20)) < 1e-9
    )
    assert valeurs(mesurer([sommet])) == {"X": 100.0, "Y": 50.0, "Z": 20.0}


def test_distance_et_ecarts_entre_deux_sommets(boite: TopoDS_Shape) -> None:
    sommets = {
        tuple(round(c, 6) for c in BRep_Tool.Pnt(topods.Vertex(s)).Coord()): s
        for s in sous_formes(boite, TopAbs_VERTEX)
    }
    resultat = valeurs(mesurer([sommets[(0, 0, 0)], sommets[(100, 50, 20)]]))
    assert resultat["Distance"] == pytest.approx(math.sqrt(100**2 + 50**2 + 20**2))
    assert (resultat["dX"], resultat["dY"], resultat["dZ"]) == (100.0, 50.0, 20.0)


def test_faces_opposees_distance_et_angle_nul(boite: TopoDS_Shape) -> None:
    faces = sous_formes(boite, TopAbs_FACE)
    dessous = next(f for f in faces if normale_plane(f) is not None and normale_plane(f).Z() < -0.9)  # type: ignore[union-attr]
    dessus = next(f for f in faces if normale_plane(f) is not None and normale_plane(f).Z() > 0.9)  # type: ignore[union-attr]
    resultat = valeurs(mesurer([dessous, dessus]))
    assert resultat["Distance"] == pytest.approx(20.0)
    assert resultat["Angle"] == pytest.approx(0.0)


def test_faces_voisines_angle_droit(boite: TopoDS_Shape) -> None:
    faces = sous_formes(boite, TopAbs_FACE)
    dessus = next(f for f in faces if normale_plane(f).Z() > 0.9)  # type: ignore[union-attr]
    cote = next(f for f in faces if normale_plane(f).X() > 0.9)  # type: ignore[union-attr]
    resultat = valeurs(mesurer([dessus, cote]))
    assert resultat["Distance"] == pytest.approx(0.0)
    assert resultat["Angle"] == pytest.approx(90.0)


def test_trou_rayon_et_diametre(boite_percee: TopoDS_Shape) -> None:
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.GeomAbs import GeomAbs_Cylinder

    cylindre = next(
        f
        for f in sous_formes(boite_percee, TopAbs_FACE)
        if BRepAdaptor_Surface(topods.Face(f)).GetType() == GeomAbs_Cylinder
    )
    resultat = valeurs(mesurer([cylindre]))
    assert resultat["Rayon"] == pytest.approx(5.0)
    assert resultat["Diamètre"] == pytest.approx(10.0)
    assert resultat["Aire"] == pytest.approx(2 * math.pi * 5 * 20)


def test_arete_circulaire(boite_percee: TopoDS_Shape) -> None:
    cercles = [
        valeurs(mesurer([a]))
        for a in sous_formes(boite_percee, TopAbs_EDGE)
        if "Rayon" in valeurs(mesurer([a]))
    ]
    assert cercles
    for cercle in cercles:
        assert cercle["Rayon"] == pytest.approx(5.0)


def test_trois_entites_rien_a_mesurer(boite: TopoDS_Shape) -> None:
    assert mesurer(sous_formes(boite, TopAbs_FACE)[:3]) == []


def test_format_francais() -> None:
    assert formater(Valeur("Longueur", 100.0, Unite.LONGUEUR)) == "Longueur : 100,00 mm"
    assert formater(Valeur("Aire", 5000.0, Unite.AIRE)) == "Aire : 5000,00 mm²"
    assert formater(Valeur("Angle", 90.0, Unite.ANGLE)) == "Angle : 90,00°"
