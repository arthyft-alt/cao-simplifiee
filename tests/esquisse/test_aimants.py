"""Tests du système d'aimant (inférence ESQ-04), demandé par Simon : points, coins,
repère, horizontale / verticale, pour des figures bien fermées et bien tenues."""

import pytest

from cao.esquisse.aimants import Axe, Orientation, aimanter
from cao.esquisse.esquisse import ORIGINE, Esquisse, GenreRelation, Ligne
from cao.esquisse.geometrie import Point2D
from cao.esquisse.outils import Clic, OutilCercle, OutilLigne
from cao.esquisse.solveur import EtatEsquisse, resoudre

TOL = 1.0  # mm


def clic_aimante(e: Esquisse, outil: object, souris: Point2D) -> object:
    """Comme l'interface : aimantation, clic, puis exécution de la modification."""
    depart = outil.point_de_depart()  # type: ignore[attr-defined]
    a = aimanter(e, souris, TOL, depart)
    modification = outil.clic(Clic(a.position, a.accroche, a.sur_axe, a.orientation))  # type: ignore[attr-defined]
    if modification is None:
        return None
    resultat = modification(e)
    outil.applique(e, resultat)  # type: ignore[attr-defined]
    return resultat


# --- Aimants seuls ---


def test_point_existant_attire_le_curseur() -> None:
    e = Esquisse()
    p = e.ajouter_point(40, 25)
    a = aimanter(e, Point2D(40.6, 24.5), TOL)
    assert a.accroche == p and a.position == (40, 25)


def test_origine_attire_le_curseur() -> None:
    a = aimanter(Esquisse(), Point2D(0.4, -0.3), TOL)
    assert a.accroche == ORIGINE and a.position == (0, 0)


def test_le_point_est_prioritaire_sur_l_axe() -> None:
    e = Esquisse()
    p = e.ajouter_point(30, 0.5)
    assert aimanter(e, Point2D(30.2, 0.2), TOL).accroche == p


def test_axes_du_repere() -> None:
    e = Esquisse()
    sur_x = aimanter(e, Point2D(25, 0.7), TOL)
    assert sur_x.sur_axe == Axe.X and sur_x.position == (25, 0)
    assert sur_x.guides  # trait pointillé le long de l'axe
    sur_y = aimanter(e, Point2D(-0.6, 18), TOL)
    assert sur_y.sur_axe == Axe.Y and sur_y.position == (0, 18)


def test_ligne_presque_horizontale_ou_verticale() -> None:
    e = Esquisse()
    depart = Point2D(10, 20)
    h = aimanter(e, Point2D(60, 20.8), TOL, depart)
    assert h.orientation == Orientation.HORIZONTALE and h.position == (60, 20)
    v = aimanter(e, Point2D(10.5, 70), TOL, depart)
    assert v.orientation == Orientation.VERTICALE and v.position == (10, 70)
    libre = aimanter(e, Point2D(40, 45), TOL, depart)
    assert libre.orientation is None and not libre.active


def test_alignement_avec_un_point_sans_relation() -> None:
    e = Esquisse()
    e.ajouter_point(30, 40)
    a = aimanter(e, Point2D(30.6, 70), TOL)
    assert a.position == (30, 70)  # même x que le point
    assert a.accroche is None and a.sur_axe is None and a.orientation is None
    assert a.guides == [(Point2D(30, 40), Point2D(30, 70))]


# --- Relations créées par les outils ---


def test_contour_aimante_devient_un_rectangle_parfait() -> None:
    """Tracé à main levée d'un contour : les aimants le ferment et le redressent."""
    e, outil = Esquisse(), OutilLigne()
    for souris in [(0.3, 0.2), (79.6, 0.6), (80.4, 30.2), (0.5, 29.6), (0.2, 0.4)]:
        clic_aimante(e, outil, Point2D(*souris))
    lignes = [c for c in e.courbes() if isinstance(c, Ligne)]
    assert len(lignes) == 4 and len(e.points()) == 3  # fermé (le 1er point est l'origine)
    assert not outil.en_cours  # la suite s'arrête quand le contour se ferme
    genres = sorted(r.genre.value for r in e.relations.values())
    assert genres.count("horizontale") == 2 and genres.count("verticale") == 2
    resultat = resoudre(e)
    assert resultat.etat == EtatEsquisse.SOUS_CONTRAINTE
    assert resultat.degres_de_liberte == 2  # il ne reste que la largeur et la hauteur


def test_point_pose_sur_un_axe_y_reste_attache() -> None:
    e, outil = Esquisse(), OutilLigne()
    clic_aimante(e, outil, Point2D(20, 0.6))  # départ sur l'axe X
    clic_aimante(e, outil, Point2D(50, 35))
    debut = e["L1"].debut  # type: ignore[union-attr]
    relation = next(iter(e.relations.values()))
    assert relation.genre == GenreRelation.HORIZONTALE
    assert sorted(relation.entites) == sorted([debut, ORIGINE])
    resoudre(e)
    assert e.position(debut).y == pytest.approx(0)


def test_centre_de_cercle_sur_l_axe() -> None:
    e, outil = Esquisse(), OutilCercle()
    clic_aimante(e, outil, Point2D(-0.4, 25))  # centre sur l'axe Y
    clic_aimante(e, outil, Point2D(10, 25))
    centre = e["C1"].centre  # type: ignore[union-attr]
    assert any(
        r.genre == GenreRelation.VERTICALE and ORIGINE in r.entites for r in e.relations.values()
    )
    assert e.position(centre).x == 0


def test_relation_horizontale_entre_deux_points() -> None:
    e = Esquisse()
    p = e.ajouter_point(30, 4)
    e.ajouter_relation(GenreRelation.HORIZONTALE, p, ORIGINE)
    assert resoudre(e).reussi
    assert e.position(p).y == pytest.approx(0)
