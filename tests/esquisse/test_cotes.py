"""Tests de l'étape 2.3 : cotes et degré de contrainte (COT-01, COT-05, ESQ-07).

Critère du plan : tests sur 5 esquisses types. Chacune part d'un tracé approximatif,
reçoit ses relations et ses cotes, et doit devenir totalement contrainte avec des
coordonnées exactes.
"""

import json
import math

import pytest

from cao.esquisse.esquisse import (
    ORIGINE,
    Cercle,
    CoteImpossible,
    Esquisse,
    GenreCote,
    GenreRelation,
    Ligne,
)
from cao.esquisse.geometrie import Point2D
from cao.esquisse.solveur import EtatEsquisse, Resultat, resoudre

G, C = GenreRelation, GenreCote


def resolu(e: Esquisse) -> Resultat:
    resultat = resoudre(e)
    assert resultat.reussi, resultat.message
    return resultat


def coins(e: Esquisse) -> list[tuple[float, float]]:
    return sorted((round(p.x, 6) + 0.0, round(p.y, 6) + 0.0) for p in e.points())


def rectangle_contraint(e: Esquisse, largeur: float, hauteur: float) -> list[str]:
    """Rectangle tracé à peu près, avec ses relations et ses deux cotes, coin à l'origine."""
    bas, droite, haut, gauche = e.ajouter_rectangle(Point2D(1.2, -0.7), Point2D(78, 31.5))
    for cote in (bas, haut):
        e.ajouter_relation(G.HORIZONTALE, cote)
    for cote in (droite, gauche):
        e.ajouter_relation(G.VERTICALE, cote)
    coin = e[bas].debut  # type: ignore[union-attr]
    e.ajouter_relation(G.COINCIDENTE, coin, ORIGINE)
    e.ajouter_cote(C.LONGUEUR, bas, valeur=largeur)
    e.ajouter_cote(C.LONGUEUR, droite, valeur=hauteur)
    return [bas, droite, haut, gauche]


# --- Les 5 esquisses types ---


def test_type_1_rectangle_80_x_30() -> None:
    e = Esquisse()
    rectangle_contraint(e, 80, 30)
    resultat = resolu(e)
    assert resultat.etat == EtatEsquisse.TOTALEMENT_CONTRAINTE
    assert resultat.degres_de_liberte == 0
    assert coins(e) == [(0, 0), (0, 30), (80, 0), (80, 30)]


def test_type_2_cercle_diametre_20_a_l_origine() -> None:
    e = Esquisse()
    c = e.ajouter_cercle((0.8, -0.4), 9.3)
    cercle = e[c]
    assert isinstance(cercle, Cercle)
    e.ajouter_relation(G.COINCIDENTE, cercle.centre, ORIGINE)
    e.ajouter_cote(C.DIAMETRE, c, valeur=20)
    resultat = resolu(e)
    assert resultat.etat == EtatEsquisse.TOTALEMENT_CONTRAINTE
    assert e.rayon(c) == pytest.approx(10)
    assert e.position(cercle.centre) == pytest.approx((0, 0))


def test_type_3_plaque_percee() -> None:
    e = Esquisse()
    rectangle_contraint(e, 100, 50)
    c = e.ajouter_cercle((48, 27), 4)
    centre = e[c].centre  # type: ignore[union-attr]
    e.ajouter_cote(C.HORIZONTALE, ORIGINE, centre, valeur=50)
    e.ajouter_cote(C.VERTICALE, ORIGINE, centre, valeur=25)
    e.ajouter_cote(C.DIAMETRE, c, valeur=10)
    resultat = resolu(e)
    assert resultat.etat == EtatEsquisse.TOTALEMENT_CONTRAINTE
    assert e.position(centre) == pytest.approx((50, 25))
    assert e.rayon(c) == pytest.approx(5)


def test_type_4_equerre_en_l() -> None:
    e = Esquisse()
    trace = [(0.5, 0.3), (61, -0.4), (60.6, 9.2), (9.4, 10.5), (10.3, 41), (-0.4, 39.6)]
    cotes = e.ajouter_lignes_chainees(trace, fermer=True)
    for i, ligne in enumerate(cotes):
        e.ajouter_relation(G.HORIZONTALE if i % 2 == 0 else G.VERTICALE, ligne)
    e.ajouter_relation(G.COINCIDENTE, e[cotes[0]].debut, ORIGINE)  # type: ignore[union-attr]
    e.ajouter_cote(C.LONGUEUR, cotes[0], valeur=60)  # base
    e.ajouter_cote(C.LONGUEUR, cotes[1], valeur=10)  # épaisseur de l'aile horizontale
    e.ajouter_cote(C.LONGUEUR, cotes[5], valeur=40)  # hauteur totale
    e.ajouter_cote(C.LONGUEUR, cotes[4], valeur=10)  # épaisseur de l'aile verticale
    resultat = resolu(e)
    assert resultat.etat == EtatEsquisse.TOTALEMENT_CONTRAINTE
    assert coins(e) == [(0, 0), (0, 40), (10, 10), (10, 40), (60, 0), (60, 10)]


def test_type_5_triangle_avec_angle() -> None:
    e = Esquisse()
    base = e.ajouter_ligne(ORIGINE, (49, 1.5))
    cote = e.ajouter_ligne(ORIGINE, (36, 22))
    e.ajouter_relation(G.HORIZONTALE, base)
    e.ajouter_cote(C.LONGUEUR, base, valeur=50)
    e.ajouter_cote(C.LONGUEUR, cote, valeur=40)
    angle = e.ajouter_cote(C.ANGLE, base, cote, valeur=30)
    resultat = resolu(e)
    assert resultat.etat == EtatEsquisse.TOTALEMENT_CONTRAINTE
    bout = e.position(e[cote].fin)  # type: ignore[union-attr]
    assert bout == pytest.approx((40 * math.cos(math.radians(30)), 20))
    assert e.cotes[angle].valeur == 30


# --- État de l'esquisse (ESQ-07) ---


def test_sous_contrainte_indique_les_degres_restants() -> None:
    e = Esquisse()
    rectangle_contraint(e, 80, 30)
    for cote in list(e.cotes):
        e.supprimer_cote(cote)
    resultat = resolu(e)
    assert resultat.etat == EtatEsquisse.SOUS_CONTRAINTE
    assert resultat.degres_de_liberte == 2  # largeur et hauteur libres


def test_sur_contrainte_designe_la_cote_en_trop() -> None:
    e = Esquisse()
    _bas, _droite, haut, _gauche = rectangle_contraint(e, 80, 30)
    en_trop = e.ajouter_cote(C.LONGUEUR, haut, valeur=81)  # contredit la largeur de 80
    resultat = resoudre(e)
    assert resultat.etat == EtatEsquisse.SUR_CONTRAINTE
    assert en_trop in resultat.conflits


# --- Cotes : pose, modification, référence ---


def test_cote_posee_prend_la_mesure_actuelle() -> None:
    e = Esquisse()
    ligne = e.ajouter_ligne((0, 0), (30, 40))
    assert e.cotes[e.ajouter_cote(C.LONGUEUR, ligne)].valeur == pytest.approx(50)


def test_modifier_une_cote_met_a_jour_la_geometrie() -> None:
    e = Esquisse()
    bas, *_ = rectangle_contraint(e, 80, 30)
    resolu(e)
    largeur = next(c.id for c in e.cotes.values() if c.entites == [bas])
    e.modifier_cote(largeur, 120)
    resolu(e)
    assert e.longueur(bas) == pytest.approx(120)


def test_cote_pilotee_mesure_sans_contraindre() -> None:
    e = Esquisse()
    _bas, _droite, haut, _gauche = rectangle_contraint(e, 80, 30)
    reference = e.ajouter_cote(C.LONGUEUR, haut, pilotee=True)
    resultat = resolu(e)
    assert resultat.etat == EtatEsquisse.TOTALEMENT_CONTRAINTE  # pas de conflit
    assert e.cotes[reference].valeur == pytest.approx(80)


def test_cote_distance_point_ligne_et_rayon_d_arc() -> None:
    e = Esquisse()
    ligne = e.ajouter_ligne(ORIGINE, (100, 0))
    e.ajouter_relation(G.HORIZONTALE, ligne)
    p = e.ajouter_point(30, 12)
    e.ajouter_cote(C.DISTANCE, p, ligne, valeur=20)
    a = e.ajouter_arc((0, 50), (8, 50), (0, 58))
    e.ajouter_cote(C.RAYON, a, valeur=15)
    resolu(e)
    assert e.position(p).y == pytest.approx(20)
    assert e.rayon(a) == pytest.approx(15)


def test_distance_entre_lignes_paralleles() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (50, 0))
    l2 = e.ajouter_ligne((0, 10), (50, 10))
    e.ajouter_relation(G.HORIZONTALE, l1)
    e.ajouter_relation(G.PARALLELE, l1, l2)
    e.ajouter_cote(C.DISTANCE, l1, l2, valeur=25)
    resolu(e)
    debut_l2 = e[l2].debut  # type: ignore[union-attr]
    assert e.position(debut_l2).y - e.position(e[l1].debut).y == pytest.approx(25)  # type: ignore[union-attr]


# --- Refus avec message clair ---


def test_refus_angle_entre_paralleles_et_distance_entre_secantes() -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (50, 0))
    l2 = e.ajouter_ligne((0, 10), (50, 10))
    l3 = e.ajouter_ligne((0, 0), (20, 30))
    with pytest.raises(CoteImpossible, match="distance entre elles"):
        e.ajouter_cote(C.ANGLE, l1, l2)
    with pytest.raises(CoteImpossible, match="cotez l'angle"):
        e.ajouter_cote(C.DISTANCE, l1, l3)
    assert e.cotes == {}


@pytest.mark.parametrize(
    ("genre", "valeur", "message"),
    [
        (C.LONGUEUR, 0, "strictement positive"),
        (C.LONGUEUR, -5, "strictement positive"),
        (C.ANGLE, 200, "entre 0 et 180"),
        (C.LONGUEUR, float("nan"), "nombre"),
    ],
)
def test_valeurs_refusees(genre: GenreCote, valeur: float, message: str) -> None:
    e = Esquisse()
    l1 = e.ajouter_ligne((0, 0), (50, 0))
    l2 = e.ajouter_ligne((0, 0), (30, 30))
    entites = (l1, l2) if genre == C.ANGLE else (l1,)
    with pytest.raises(CoteImpossible, match=message):
        e.ajouter_cote(genre, *entites, valeur=valeur)


def test_origine_ne_bouge_pas_et_n_est_pas_enregistree() -> None:
    e = Esquisse()
    e.deplacer_point(ORIGINE, 5, 5)
    assert e.position(ORIGINE) == (0, 0)
    assert ORIGINE not in json.dumps(e.vers_dict())


# --- Enregistrement et suppression ---


def test_cotes_enregistrees_et_relues() -> None:
    e = Esquisse()
    rectangle_contraint(e, 80, 30)
    e.ajouter_cote(C.LONGUEUR, "L3", pilotee=True)
    relue = Esquisse.depuis_dict(json.loads(json.dumps(e.vers_dict())))
    assert relue.vers_dict() == e.vers_dict()
    assert relue.ajouter_cote(C.LONGUEUR, "L4") == "D4"


def test_supprimer_une_ligne_retire_ses_cotes() -> None:
    e = Esquisse()
    bas, *_ = rectangle_contraint(e, 80, 30)
    supprimes = e.supprimer(bas)
    assert not any(bas in c.entites for c in e.cotes.values())
    assert any(s.startswith("D") for s in supprimes)
    ligne = e["L2"]
    assert isinstance(ligne, Ligne)
