"""Tests de l'étape 2.6 (sans écran) : cotation intelligente (tableau 3.5) et unités (COT-06)."""

import pytest

from cao.document.unites import SaisieInvalide, UniteLongueur, Unites
from cao.esquisse.cotation import deduire_cote
from cao.esquisse.esquisse import CoteImpossible, Esquisse, GenreCote
from cao.esquisse.geometrie import Point2D

C = GenreCote


@pytest.fixture
def e() -> Esquisse:
    return Esquisse()


# --- Les 7 cas du tableau 3.5 du cahier des charges ---


def test_une_ligne_horizontale_donne_sa_longueur(e: Esquisse) -> None:
    ligne = e.ajouter_ligne((0, 0), (80, 0))
    assert deduire_cote(e, [ligne], Point2D(40, 15)) == (C.LONGUEUR, [ligne])


@pytest.mark.parametrize(
    ("curseur", "genre"),
    [
        (Point2D(20, 60), C.HORIZONTALE),  # au-dessus de la ligne
        (Point2D(60, 20), C.VERTICALE),  # à droite de la ligne
        (Point2D(25, 15), C.LONGUEUR),  # le long de la ligne : alignée
    ],
)
def test_une_ligne_inclinee_selon_le_curseur(
    e: Esquisse, curseur: Point2D, genre: GenreCote
) -> None:
    ligne = e.ajouter_ligne((0, 0), (40, 30))
    assert deduire_cote(e, [ligne], curseur)[0] == genre


def test_deux_points_distance(e: Esquisse) -> None:
    p1, p2 = e.ajouter_point(0, 0), e.ajouter_point(30, 0)
    assert deduire_cote(e, [p1, p2]) == (C.LONGUEUR, [p1, p2])


def test_point_et_ligne_distance(e: Esquisse) -> None:
    ligne = e.ajouter_ligne((0, 0), (80, 0))
    p = e.ajouter_point(30, 20)
    assert deduire_cote(e, [ligne, p])[0] == C.DISTANCE


def test_deux_lignes_secantes_angle_paralleles_distance(e: Esquisse) -> None:
    l1 = e.ajouter_ligne((0, 0), (80, 0))
    l2 = e.ajouter_ligne((0, 0), (40, 30))
    l3 = e.ajouter_ligne((0, 20), (80, 20))
    assert deduire_cote(e, [l1, l2])[0] == C.ANGLE
    assert deduire_cote(e, [l1, l3])[0] == C.DISTANCE


def test_cercle_diametre_arc_rayon(e: Esquisse) -> None:
    c = e.ajouter_cercle((0, 0), 10)
    a = e.ajouter_arc((50, 0), (60, 0), (50, 10))
    assert deduire_cote(e, [c]) == (C.DIAMETRE, [c])
    assert deduire_cote(e, [a]) == (C.RAYON, [a])


def test_cercle_et_ligne_distance_du_centre(e: Esquisse) -> None:
    c = e.ajouter_cercle((40, 25), 5)
    ligne = e.ajouter_ligne((0, 0), (100, 0))
    genre, entites = deduire_cote(e, [c, ligne])
    assert genre == C.DISTANCE
    assert entites == [e[c].centre, ligne]  # type: ignore[union-attr]


def test_deux_cercles_entraxe(e: Esquisse) -> None:
    c1, c2 = e.ajouter_cercle((0, 0), 5), e.ajouter_cercle((60, 0), 8)
    genre, entites = deduire_cote(e, [c1, c2])
    assert genre == C.LONGUEUR
    assert entites == [e[c1].centre, e[c2].centre]  # type: ignore[union-attr]
    # La cote obtenue se pose sans erreur et mesure l'entraxe.
    cote = e.ajouter_cote(genre, *entites)
    assert e.cotes[cote].valeur == pytest.approx(60)


def test_selection_impossible(e: Esquisse) -> None:
    p = e.ajouter_point(0, 0)
    with pytest.raises(CoteImpossible, match="sélectionnez"):
        deduire_cote(e, [p])
    l1 = e.ajouter_ligne((0, 0), (1, 0))
    l2 = e.ajouter_ligne((0, 1), (1, 1))
    l3 = e.ajouter_ligne((0, 2), (1, 2))
    with pytest.raises(CoteImpossible):
        deduire_cote(e, [l1, l2, l3])


# --- Unités (COT-06) ---


def test_affichage_selon_l_unite_et_la_precision() -> None:
    assert Unites().formater_longueur(80) == "80,00 mm"
    assert Unites(UniteLongueur.CM, 1).formater_longueur(125) == "12,5 cm"
    assert Unites(UniteLongueur.POUCE, 3).formater_longueur(25.4) == "1,000 in"
    assert Unites(decimales=0).formater_angle(30.4) == "30°"
    assert Unites().formater_longueur(-0.001) == "0,00 mm"


def test_saisie_avec_virgule_point_ou_unite() -> None:
    u = Unites()
    assert u.lire_longueur("12,5") == 12.5
    assert u.lire_longueur(" 12.5 ") == 12.5
    assert u.lire_longueur("2,5 cm") == 25
    assert u.lire_longueur("1 in") == pytest.approx(25.4)
    assert Unites(UniteLongueur.CM).lire_longueur("3") == 30
    assert u.lire_angle("30°") == 30


@pytest.mark.parametrize("texte", ["", "abc", "12 km", "1,2,3"])
def test_saisie_refusee(texte: str) -> None:
    with pytest.raises(SaisieInvalide):
        Unites().lire_longueur(texte)


def test_valeur_proposee_dans_le_champ() -> None:
    assert Unites().valeur_saisie_longueur(80) == "80"
    assert Unites().valeur_saisie_longueur(12.5) == "12,5"
    assert Unites(UniteLongueur.CM).valeur_saisie_longueur(125) == "12,5"


def test_reglages_enregistres() -> None:
    u = Unites(UniteLongueur.CM, 1)
    assert Unites.depuis_dict(u.vers_dict()) == u


# --- Position de la cote (déport) : elle passe là où se trouve la souris ---
# Règle constatée sur OpenCascade (essai réel du 2026-10-31) pour les cotes horizontales
# et verticales : déport mesuré depuis le 2e point, vers le haut (horizontale) ou vers la
# gauche (verticale). Régression signalée par Simon : la cote « montait haut ».


@pytest.mark.parametrize("sens", ["vers la droite", "vers la gauche"])
def test_deport_cote_horizontale_suit_la_souris(e: Esquisse, sens: str) -> None:
    from cao.esquisse.cotation import deport_pour

    ligne = (
        e.ajouter_ligne((0, 0), (40, 30))
        if sens == "vers la droite"
        else e.ajouter_ligne((40, 30), (0, 0))
    )
    second = e.position(e[ligne].fin)  # type: ignore[union-attr]
    for y in (50.0, -20.0):
        deport = deport_pour(e, C.HORIZONTALE, [ligne], Point2D(20, y))
        assert second.y + deport == pytest.approx(
            y
        )  # la ligne de cote passe à la hauteur de la souris


@pytest.mark.parametrize("sens", ["vers la droite", "vers la gauche"])
def test_deport_cote_verticale_suit_la_souris(e: Esquisse, sens: str) -> None:
    from cao.esquisse.cotation import deport_pour

    ligne = (
        e.ajouter_ligne((0, 0), (40, 30))
        if sens == "vers la droite"
        else e.ajouter_ligne((40, 30), (0, 0))
    )
    second = e.position(e[ligne].fin)  # type: ignore[union-attr]
    for x in (-15.0, 60.0):
        deport = deport_pour(e, C.VERTICALE, [ligne], Point2D(x, 15))
        assert second.x - deport == pytest.approx(x)


@pytest.mark.parametrize(
    ("selection", "curseur"),
    [
        (["L4", "L2"], Point2D(40, 50)),  # côtés verticaux, souris au-dessus
        (["L2", "L4"], Point2D(40, 50)),  # même chose, cliqués dans l'autre ordre
        (["L4", "L2"], Point2D(40, -20)),  # souris au-dessous
        (["L1", "L3"], Point2D(100, 15)),  # côtés horizontaux, souris à droite
        (["L3", "L1"], Point2D(-20, 15)),  # souris à gauche
    ],
)
def test_distance_entre_cotes_paralleles_suit_la_souris(
    e: Esquisse, selection: list[str], curseur: Point2D
) -> None:
    """Régression signalée par Simon : la cote entre deux côtés parallèles se plaçait mal."""
    from cao.esquisse.cotation import deport_pour, points_mesures

    e.ajouter_rectangle(Point2D(0, 0), Point2D(80, 30))  # L1 bas, L2 droite, L3 haut, L4 gauche
    genre, entites = deduire_cote(e, selection, curseur)
    assert genre == C.DISTANCE
    a, b = points_mesures(e, genre, entites)
    deport = deport_pour(e, genre, entites, curseur)
    # La ligne de cote est décalée de `deport` vers la gauche du segment a -> b :
    # elle doit passer à la même distance du segment que la souris.
    d = b - a
    gauche = Point2D(-d.y / d.norme(), d.x / d.norme())
    ecart_souris = (curseur.x - a.x) * gauche.x + (curseur.y - a.y) * gauche.y
    assert deport == pytest.approx(ecart_souris)
