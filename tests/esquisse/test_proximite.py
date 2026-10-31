"""Recherche de l'entité la plus proche du curseur (sélection pour la cotation)."""

from cao.esquisse.esquisse import ORIGINE, Esquisse
from cao.esquisse.geometrie import Point2D
from cao.esquisse.proximite import entite_proche

TOL = 1.0


def test_point_prioritaire_sur_la_ligne() -> None:
    e = Esquisse()
    ligne = e.ajouter_ligne((10, 0), (50, 0))
    debut = e[ligne].debut  # type: ignore[union-attr]
    assert entite_proche(e, Point2D(10.5, 0.2), TOL) == debut  # sur la ligne ET près du point
    assert entite_proche(e, Point2D(30, 0.4), TOL) == ligne  # milieu de la ligne


def test_origine_selectionnable() -> None:
    assert entite_proche(Esquisse(), Point2D(0.3, -0.2), TOL) == ORIGINE


def test_cercle_et_arc() -> None:
    e = Esquisse()
    c = e.ajouter_cercle((0, 50), 10)
    a = e.ajouter_arc((50, 50), (60, 50), (50, 60))  # quart d'arc en haut à droite
    assert entite_proche(e, Point2D(0, 60.5), TOL) == c
    assert entite_proche(e, Point2D(50 + 7.07, 50 + 7.4), TOL) == a  # en face de l'arc
    assert entite_proche(e, Point2D(40, 50), TOL) is None  # sur le cercle porteur, hors de l'arc


def test_rien_a_proximite() -> None:
    e = Esquisse()
    e.ajouter_ligne((10, 0), (50, 0))
    assert entite_proche(e, Point2D(30, 5), TOL) is None
