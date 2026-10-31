"""Tests de l'étape 2.2 : relations géométriques et solveur (REL-01 à REL-05).

Critère du plan : un test par relation. Chaque test part d'un tracé volontairement
approximatif (comme un tracé à la souris), ajoute la relation, résout, puis
vérifie la propriété géométrique obtenue.
"""

import json

import pytest

from cao.esquisse.esquisse import Esquisse, GenreRelation, Ligne, RelationImpossible
from cao.esquisse.geometrie import Point2D, distance
from cao.esquisse.solveur import EtatEsquisse, angle_entre_lignes, resoudre

G = GenreRelation
PRECISION = 1e-6


def ligne(e: Esquisse, identifiant: str) -> Ligne:
    entite = e[identifiant]
    assert isinstance(entite, Ligne)
    return entite


def extremites(e: Esquisse, identifiant: str) -> tuple[Point2D, Point2D]:
    l_ = ligne(e, identifiant)
    return e.position(l_.debut), e.position(l_.fin)


def resolu(e: Esquisse) -> None:
    resultat = resoudre(e)
    assert resultat.reussi, resultat.message


def distance_point_droite(p: Point2D, a: Point2D, b: Point2D) -> float:
    ab = b - a
    return abs(ab.x * (p.y - a.y) - ab.y * (p.x - a.x)) / ab.norme()


# --- REL-01 ---


def test_horizontale() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (50, 4))
    e.ajouter_relation(G.HORIZONTALE, l1)
    resolu(e)
    a, b = extremites(e, l1)
    assert a.y == pytest.approx(b.y, abs=PRECISION)


def test_verticale() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (3, 40))
    e.ajouter_relation(G.VERTICALE, l1)
    resolu(e)
    a, b = extremites(e, l1)
    assert a.x == pytest.approx(b.x, abs=PRECISION)


# --- REL-02 ---


def test_coincidente_point_point() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (10, 0))
    l2 = e.ajouter_ligne((10.4, 0.3), (20, 5))
    e.ajouter_relation(G.COINCIDENTE, ligne(e, l1).fin, ligne(e, l2).debut)
    resolu(e)
    assert e.position(ligne(e, l1).fin) == pytest.approx(e.position(ligne(e, l2).debut))


def test_coincidente_point_sur_ligne() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (100, 0))
    p = e.ajouter_point(40, 7)
    e.ajouter_relation(G.COINCIDENTE, l1, p)  # ordre indifférent
    resolu(e)
    assert distance_point_droite(e.position(p), *extremites(e, l1)) == pytest.approx(0, abs=1e-6)


def test_coincidente_point_sur_cercle() -> None:
    e = Esquisse()
    c = e.ajouter_cercle((0, 0), 10)
    p = e.ajouter_point(13, 2)
    e.ajouter_relation(G.FIXE, e[c].centre)  # type: ignore[union-attr]
    e.ajouter_relation(G.COINCIDENTE, p, c)
    resolu(e)
    assert distance(e.position(p), Point2D(0, 0)) == pytest.approx(e.rayon(c))


def test_coincidente_point_sur_arc() -> None:
    e = Esquisse()
    a = e.ajouter_arc((0, 0), (10, 0), (0, 10))
    p = e.ajouter_point(9, 9)
    e.ajouter_relation(G.COINCIDENTE, p, a)
    resolu(e)
    centre = e.position(e[a].centre)  # type: ignore[union-attr]
    assert distance(e.position(p), centre) == pytest.approx(e.rayon(a))


def test_point_milieu() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (60, 0))
    p = e.ajouter_point(25, 4)
    e.ajouter_relation(G.POINT_MILIEU, p, l1)
    resolu(e)
    a, b = extremites(e, l1)
    assert e.position(p) == pytest.approx(((a.x + b.x) / 2, (a.y + b.y) / 2))


def test_fixe() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((5, 5), (30, 9))
    debut = ligne(e, l1).debut
    e.ajouter_relation(G.FIXE, debut)
    e.ajouter_relation(G.HORIZONTALE, l1)
    resolu(e)
    assert e.position(debut) == pytest.approx((5, 5))  # le point fixe n'a pas bougé


# --- REL-03 ---


def test_parallele() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (50, 10))
    l2 = e.ajouter_ligne((0, 20), (50, 33))
    e.ajouter_relation(G.PARALLELE, l1, l2)
    resolu(e)
    assert angle_entre_lignes(e, l1, l2) == pytest.approx(0, abs=1e-4)


def test_perpendiculaire() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (50, 5))
    l2 = e.ajouter_ligne((60, 0), (55, 40))
    e.ajouter_relation(G.PERPENDICULAIRE, l1, l2)
    resolu(e)
    assert angle_entre_lignes(e, l1, l2) == pytest.approx(90, abs=1e-4)


def test_colineaire() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (40, 0))
    l2 = e.ajouter_ligne((60, 3), (90, 6))
    e.ajouter_relation(G.COLINEAIRE, l1, l2)
    resolu(e)
    a, b = extremites(e, l1)
    for p in extremites(e, l2):
        assert distance_point_droite(p, a, b) == pytest.approx(0, abs=1e-6)


# --- REL-04 ---


def test_tangente_ligne_cercle() -> None:
    e = Esquisse()
    c = e.ajouter_cercle((0, 0), 10)
    l1 = e.ajouter_ligne((-30, 13), (30, 12))
    e.ajouter_relation(G.TANGENTE, l1, c)
    resolu(e)
    centre = e.position(e[c].centre)  # type: ignore[union-attr]
    assert distance_point_droite(centre, *extremites(e, l1)) == pytest.approx(e.rayon(c))


def test_tangente_ligne_arc_a_extremite_commune() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((-20, 1), (0, 0))
    a = e.ajouter_arc((0, 10), (0, 0), (10, 10))  # part de la fin de la ligne
    arc = e[a]
    e.ajouter_relation(G.COINCIDENTE, ligne(e, l1).fin, arc.debut)  # type: ignore[union-attr]
    e.ajouter_relation(G.TANGENTE, l1, a)
    resolu(e)
    centre = e.position(arc.centre)  # type: ignore[union-attr]
    assert distance_point_droite(centre, *extremites(e, l1)) == pytest.approx(e.rayon(a), rel=1e-6)


def test_tangente_deux_cercles() -> None:
    e = Esquisse()
    c1 = e.ajouter_cercle((0, 0), 10)
    c2 = e.ajouter_cercle((27, 3), 12)
    e.ajouter_relation(G.FIXE, e[c1].centre)  # type: ignore[union-attr]
    e.ajouter_relation(G.TANGENTE, c1, c2)
    resolu(e)
    entraxe = distance(e.position(e[c1].centre), e.position(e[c2].centre))  # type: ignore[union-attr]
    assert entraxe == pytest.approx(e.rayon(c1) + e.rayon(c2), rel=1e-6)


def test_concentrique() -> None:
    e = Esquisse()
    c1 = e.ajouter_cercle((0, 0), 10)
    c2 = e.ajouter_cercle((1.5, -0.8), 20)
    e.ajouter_relation(G.CONCENTRIQUE, c1, c2)
    resolu(e)
    assert e.position(e[c1].centre) == pytest.approx(e.position(e[c2].centre))  # type: ignore[union-attr]


# --- REL-05 ---


def test_egale_lignes() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (40, 0))
    l2 = e.ajouter_ligne((0, 10), (55, 10))
    e.ajouter_relation(G.EGALE, l1, l2)
    resolu(e)
    assert e.longueur(l1) == pytest.approx(e.longueur(l2))


def test_egale_rayons_cercle_et_arc() -> None:
    e = Esquisse()
    c = e.ajouter_cercle((0, 0), 6)
    a = e.ajouter_arc((30, 0), (40, 0), (30, 10))
    e.ajouter_relation(G.EGALE, c, a)
    resolu(e)
    assert e.rayon(c) == pytest.approx(e.rayon(a))


# --- Degrés de liberté et conflits (ESQ-07) ---


def test_rectangle_avec_relations_reste_sous_contraint() -> None:
    e = Esquisse()
    bas, droite, haut, gauche = e.ajouter_rectangle(Point2D(0, 0), Point2D(80, 30))
    for cote in (bas, haut):
        e.ajouter_relation(G.HORIZONTALE, cote)
    for cote in (droite, gauche):
        e.ajouter_relation(G.VERTICALE, cote)
    resultat = resoudre(e)
    # 8 coordonnées - 4 relations : 4 degrés (position x, y, largeur, hauteur).
    assert resultat.etat == EtatEsquisse.SOUS_CONTRAINTE
    assert resultat.degres_de_liberte == 4


def test_conflit_designe_les_relations_et_ne_modifie_rien() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (50, 10))
    l2 = e.ajouter_ligne((0, 20), (50, 40))
    e.ajouter_relation(G.PARALLELE, l1, l2)
    e.ajouter_relation(G.HORIZONTALE, l1)
    conflit = e.ajouter_relation(G.PERPENDICULAIRE, l1, l2)  # impossible avec « parallèle »
    avant = json.dumps(e.vers_dict())
    resultat = resoudre(e)
    assert resultat.etat == EtatEsquisse.SUR_CONTRAINTE
    assert conflit in resultat.conflits
    assert "conflit" in resultat.message
    assert json.dumps(e.vers_dict()) == avant  # rien n'a bougé


def test_esquisse_sans_relation() -> None:
    e = Esquisse()
    e.ajouter_ligne((0, 0), (10, 0))
    resultat = resoudre(e)
    assert resultat.etat == EtatEsquisse.SOUS_CONTRAINTE
    assert resultat.degres_de_liberte == 4


# --- Modèle ---


def test_relation_refusee_avec_message_clair() -> None:
    e = Esquisse()
    c = e.ajouter_cercle((0, 0), 5)
    with pytest.raises(RelationImpossible, match="demande une ligne"):
        e.ajouter_relation(G.HORIZONTALE, c)
    l1 = e.ajouter_ligne((0, 0), (1, 0))
    with pytest.raises(RelationImpossible, match="différentes"):
        e.ajouter_relation(G.PARALLELE, l1, l1)


def test_relation_en_double_non_ajoutee() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (1, 0))
    l2 = e.ajouter_ligne((0, 1), (1, 1))
    r1 = e.ajouter_relation(G.PARALLELE, l1, l2)
    assert e.ajouter_relation(G.PARALLELE, l2, l1) == r1
    assert len(e.relations) == 1


def test_supprimer_une_entite_retire_ses_relations() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (1, 0))
    l2 = e.ajouter_ligne((0, 1), (1, 1))
    r = e.ajouter_relation(G.PARALLELE, l1, l2)
    e.ajouter_relation(G.HORIZONTALE, l2)
    supprimes = e.supprimer(l1)
    assert r in supprimes
    assert [x.genre for x in e.relations.values()] == [G.HORIZONTALE]


def test_relations_enregistrees_et_relues() -> None:
    e = Esquisse()
    bas, *_ = e.ajouter_rectangle(Point2D(0, 0), Point2D(80, 30))
    e.ajouter_relation(G.HORIZONTALE, bas)
    relue = Esquisse.depuis_dict(json.loads(json.dumps(e.vers_dict())))
    assert relue.vers_dict() == e.vers_dict()
    assert relue.ajouter_relation(G.FIXE, "P1") == "R2"
