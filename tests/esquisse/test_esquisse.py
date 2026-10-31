"""Tests de l'étape 2.1 : modèle de données de l'esquisse (GEO-01 à 04, GEO-09, ESQ-08).

Critère du plan : tests de création et de sérialisation.
"""

import json
import math

import pytest

from cao.esquisse.esquisse import Arc, Cercle, EntiteInconnue, Esquisse, Ligne, Point
from cao.esquisse.geometrie import (
    GeometrieImpossible,
    Point2D,
    arc_tangent,
    cercle_trois_points,
    distance,
    rectangle_trois_points,
)

# --- Géométrie ---


def test_cercle_trois_points() -> None:
    centre, rayon = cercle_trois_points(Point2D(10, 0), Point2D(0, 10), Point2D(-10, 0))
    assert centre == pytest.approx((0, 0))
    assert rayon == pytest.approx(10)


def test_trois_points_alignes_refuses() -> None:
    with pytest.raises(GeometrieImpossible, match="alignés"):
        cercle_trois_points(Point2D(0, 0), Point2D(1, 1), Point2D(2, 2))


def test_arc_tangent_continue_sans_cassure() -> None:
    # Ligne horizontale vers la droite qui finit en (10, 0) ; arc jusqu'en (20, 10).
    centre, debut, fin = arc_tangent(Point2D(10, 0), Point2D(1, 0), Point2D(20, 10))
    assert centre == pytest.approx((10, 10))  # rayon perpendiculaire à la ligne : tangence
    assert (debut, fin) == (Point2D(10, 0), Point2D(20, 10))  # tourne à gauche : sens trigo


def test_arc_tangent_vers_la_droite_inverse_les_extremites() -> None:
    centre, debut, fin = arc_tangent(Point2D(10, 0), Point2D(1, 0), Point2D(20, -10))
    assert centre == pytest.approx((10, -10))
    assert (debut, fin) == (Point2D(20, -10), Point2D(10, 0))


def test_rectangle_trois_points_a_des_angles_droits() -> None:
    a, b, c, d = rectangle_trois_points(Point2D(0, 0), Point2D(30, 40), Point2D(10, 60))
    cote1, cote2 = b - a, d - a
    assert cote1.x * cote2.x + cote1.y * cote2.y == pytest.approx(0)  # perpendiculaires
    assert distance(a, b) == pytest.approx(50)
    assert distance(b, c) == pytest.approx(distance(a, d))


# --- Création ---


def test_ligne_point_a_point() -> None:
    e = Esquisse()
    ligne = e.ajouter_ligne((0, 0), (30, 40))
    assert e.longueur(ligne) == pytest.approx(50)
    assert [p.id for p in e.points()] == ["P1", "P2"]
    assert ligne == "L1"


def test_lignes_chainees_partagent_leurs_points() -> None:
    e = Esquisse()
    l1, l2, _l3 = e.ajouter_lignes_chainees([(0, 0), (10, 0), (10, 10), (0, 10)])
    ligne1, ligne2 = e[l1], e[l2]
    assert isinstance(ligne1, Ligne) and isinstance(ligne2, Ligne)
    assert ligne1.fin == ligne2.debut
    assert len(e.points()) == 4
    assert e.utilisateurs(ligne1.fin) == [l1, l2]


def test_rectangle_ferme_a_quatre_coins_partages() -> None:
    e = Esquisse()
    cotes = e.ajouter_rectangle(Point2D(0, 0), Point2D(80, 30))
    assert len(cotes) == 4 and len(e.points()) == 4
    assert sorted(round(e.longueur(c)) for c in cotes) == [30, 30, 80, 80]
    for p in e.points():
        assert len(e.utilisateurs(p.id)) == 2  # chaque coin relie deux côtés : contour fermé


def test_rectangle_centre() -> None:
    e = Esquisse()
    e.ajouter_rectangle_centre(Point2D(0, 0), Point2D(40, 15))
    xs = sorted({p.x for p in e.points()})
    ys = sorted({p.y for p in e.points()})
    assert (xs, ys) == ([-40, 40], [-15, 15])


def test_rectangle_plat_refuse() -> None:
    with pytest.raises(GeometrieImpossible):
        Esquisse().ajouter_rectangle(Point2D(0, 0), Point2D(10, 0))


def test_cercle_centre_rayon_et_trois_points() -> None:
    e = Esquisse()
    c1 = e.ajouter_cercle((0, 0), 5)
    c2 = e.ajouter_cercle_trois_points(Point2D(10, 0), Point2D(0, 10), Point2D(-10, 0))
    assert e.rayon(c1) == 5
    assert e.rayon(c2) == pytest.approx(10)
    assert e.longueur(c1) == pytest.approx(10 * math.pi)


def test_cercle_de_rayon_nul_refuse() -> None:
    with pytest.raises(GeometrieImpossible):
        Esquisse().ajouter_cercle((0, 0), 0)


def test_arc_centre_extremites_ramene_la_fin_sur_le_cercle() -> None:
    e = Esquisse()
    a = e.ajouter_arc((0, 0), (10, 0), (0, 3))  # la fin ne donne que l'angle
    arc = e[a]
    assert isinstance(arc, Arc)
    assert e.position(arc.fin) == pytest.approx((0, 10))
    assert e.angle_arc(a) == pytest.approx(math.pi / 2)
    assert e.longueur(a) == pytest.approx(10 * math.pi / 2)


def test_arc_trois_points() -> None:
    e = Esquisse()
    a = e.ajouter_arc_trois_points(Point2D(10, 0), Point2D(0, 10), Point2D(-10, 0))
    assert e.rayon(a) == pytest.approx(10)
    assert e.angle_arc(a) == pytest.approx(math.pi)


def test_arc_tangent_part_du_bout_de_la_ligne() -> None:
    e = Esquisse()
    ligne = e.ajouter_ligne((0, 0), (10, 0))
    a = e.ajouter_arc_tangent(ligne, Point2D(20, 10))
    arc, segment = e[a], e[ligne]
    assert isinstance(arc, Arc) and isinstance(segment, Ligne)
    assert arc.debut == segment.fin  # point partagé : pas de trou
    assert e.rayon(a) == pytest.approx(10)


def test_point_de_construction_et_ligne_de_construction() -> None:
    e = Esquisse()
    p = e.ajouter_point(5, 5, construction=True)
    axe = e.ajouter_ligne((0, -50), (0, 50), construction=True)
    assert e.point(p).construction
    assert e[axe].construction
    e.basculer_construction(axe)
    assert not e[axe].construction


def test_ligne_de_longueur_nulle_refusee_sans_laisser_de_points() -> None:
    e = Esquisse()
    libre = e.ajouter_point(3, 3)
    with pytest.raises(GeometrieImpossible):
        e.ajouter_ligne((1, 1), (1, 1))
    with pytest.raises(GeometrieImpossible):
        e.ajouter_ligne(libre, (3, 3))
    assert [p.id for p in e.points()] == [libre]  # le point existant est conservé


def test_point_inconnu() -> None:
    with pytest.raises(EntiteInconnue):
        Esquisse().ajouter_ligne("P99", (1, 1))


# --- Suppression ---


def test_supprimer_une_ligne_garde_les_points_partages() -> None:
    e = Esquisse()
    l1, l2 = e.ajouter_lignes_chainees([(0, 0), (10, 0), (10, 10)])
    supprimes = e.supprimer(l1)
    assert supprimes == [l1, "P1"]  # P2 sert encore à l2
    assert l2 in e.entites and "P2" in e.entites


def test_supprimer_un_point_supprime_ses_courbes() -> None:
    e = Esquisse()
    e.ajouter_lignes_chainees([(0, 0), (10, 0), (10, 10)])
    e.supprimer("P2")
    assert e.courbes() == []
    assert e.entites == {}


# --- Enregistrement ---


def test_aller_retour_dict_et_json() -> None:
    e = Esquisse("Esquisse1", "dessus")
    e.ajouter_rectangle(Point2D(0, 0), Point2D(80, 30))
    e.ajouter_cercle((40, 15), 5)
    ligne = e.ajouter_ligne((0, -10), (80, -10), construction=True)
    e.ajouter_arc_tangent(ligne, Point2D(90, 0))
    texte = json.dumps(e.vers_dict())
    relue = Esquisse.depuis_dict(json.loads(texte))
    assert relue.vers_dict() == e.vers_dict()
    assert relue.plan == "dessus"


def test_numerotation_continue_apres_relecture() -> None:
    e = Esquisse()
    e.ajouter_ligne((0, 0), (1, 0))
    relue = Esquisse.depuis_dict(e.vers_dict())
    assert relue.ajouter_ligne((0, 1), (1, 1)) == "L2"
    assert relue.ajouter_point(5, 5) == "P5"


def test_types_d_entites() -> None:
    e = Esquisse()
    e.ajouter_ligne((0, 0), (1, 0))
    e.ajouter_cercle((0, 0), 1)
    e.ajouter_arc((0, 0), (2, 0), (0, 2))
    genres = {type(x) for x in e.entites.values()}
    assert genres == {Point, Ligne, Cercle, Arc}
