"""Tests de l'étape 2.4 (partie sans écran) : outils de tracé, plans, pièce et annulation."""

import pytest

from cao.document.document import Document
from cao.document.historique import PileAnnulation
from cao.esquisse.esquisse import ORIGINE, Arc, Esquisse, GenreRelation, Ligne
from cao.esquisse.geometrie import GeometrieImpossible, Point2D
from cao.esquisse.outils import Clic, OutilArc, OutilCercle, OutilLigne, OutilRectangle
from cao.esquisse.plans import PLANS
from cao.fichiers import format_natif
from cao.fichiers.types_documents import TypeDocument
from cao.piece.piece import CommandeAjouterEsquisse, CommandeEsquisse, Piece


def appliquer(esquisse: Esquisse, outil: object, clic: Clic) -> object:
    """Comme l'interface : clic, puis exécution de la modification éventuelle."""
    modification = outil.clic(clic)  # type: ignore[attr-defined]
    if modification is None:
        return None
    resultat = modification(esquisse)
    outil.applique(esquisse, resultat)  # type: ignore[attr-defined]
    return resultat


# --- Plans ---


@pytest.mark.parametrize("nom", ["face", "dessus", "droite"])
def test_aller_retour_plan_espace(nom: str) -> None:
    plan = PLANS[nom]
    assert plan.vers_plan(plan.vers_espace(12.5, -7)) == pytest.approx((12.5, -7))


def test_normales_des_plans() -> None:
    assert PLANS["face"].normale == (0, 0, 1)
    assert PLANS["dessus"].normale == (0, 1, 0)
    assert PLANS["droite"].normale == (1, 0, 0)


# --- Outils ---


def test_ligne_chainee_puis_refermee_sur_le_premier_point() -> None:
    e, outil = Esquisse(), OutilLigne()
    appliquer(e, outil, Clic(Point2D(0, 0)))
    l1 = appliquer(e, outil, Clic(Point2D(50, 0)))
    l2 = appliquer(e, outil, Clic(Point2D(50, 30)))
    premier = e[str(l1)].debut  # type: ignore[union-attr]
    l3 = appliquer(e, outil, Clic(Point2D(0.1, 0.1), accroche=premier))  # clic sur le 1er point
    assert len(e.courbes()) == 3 and len(e.points()) == 3  # triangle fermé, points partagés
    assert e[str(l2)].debut == e[str(l1)].fin  # type: ignore[union-attr]
    assert e[str(l3)].fin == premier  # type: ignore[union-attr]
    assert not outil.en_cours  # la suite s'arrête quand le contour est fermé


def test_ligne_accrochee_a_l_origine() -> None:
    e, outil = Esquisse(), OutilLigne()
    appliquer(e, outil, Clic(Point2D(0.2, -0.1), accroche=ORIGINE))
    ligne = appliquer(e, outil, Clic(Point2D(40, 0)))
    assert e[str(ligne)].debut == ORIGINE  # type: ignore[union-attr]


def test_echap_abandonne_la_ligne_en_cours() -> None:
    e, outil = Esquisse(), OutilLigne()
    appliquer(e, outil, Clic(Point2D(0, 0)))
    outil.abandonner()
    assert not outil.en_cours
    assert appliquer(e, outil, Clic(Point2D(10, 0))) is None  # nouveau départ
    assert e.courbes() == []


def test_apercu_de_ligne_suit_la_souris() -> None:
    outil = OutilLigne()
    assert outil.apercu(Point2D(5, 5)).vide
    outil.clic(Clic(Point2D(0, 0)))
    assert outil.apercu(Point2D(5, 5)).lignes == [(Point2D(0, 0), Point2D(5, 5))]


def test_rectangle_accroche_a_l_origine_y_est_relie() -> None:
    e, outil = Esquisse(), OutilRectangle()
    appliquer(e, outil, Clic(Point2D(0.3, 0.2), accroche=ORIGINE))
    cotes = appliquer(e, outil, Clic(Point2D(80, 30)))
    assert isinstance(cotes, list) and len(cotes) == 4
    genres = sorted(r.genre.value for r in e.relations.values())
    assert genres == ["coincidente", "horizontale", "horizontale", "verticale", "verticale"]
    coincidence = next(r for r in e.relations.values() if r.genre == GenreRelation.COINCIDENTE)
    assert ORIGINE in coincidence.entites


def test_apercu_rectangle() -> None:
    outil = OutilRectangle()
    outil.clic(Clic(Point2D(0, 0)))
    assert len(outil.apercu(Point2D(20, 10)).lignes) == 4
    assert outil.apercu(Point2D(20, 0)).vide  # rectangle plat : rien à montrer


def test_cercle_centre_puis_rayon() -> None:
    e, outil = Esquisse(), OutilCercle()
    appliquer(e, outil, Clic(Point2D(10, 10)))
    c = appliquer(e, outil, Clic(Point2D(13, 14)))
    assert e.rayon(str(c)) == pytest.approx(5)


def test_arc_trois_points_relie_a_une_ligne() -> None:
    e = Esquisse()
    ligne = e.ajouter_ligne((-20, 0), (0, 0))
    bout = e[ligne].fin  # type: ignore[union-attr]
    outil = OutilArc()
    appliquer(e, outil, Clic(Point2D(0, 0), accroche=bout))
    appliquer(e, outil, Clic(Point2D(20, 0)))
    a = appliquer(e, outil, Clic(Point2D(10, 10)))
    arc = e[str(a)]
    assert isinstance(arc, Arc)
    assert e.rayon(arc.id) == pytest.approx(10)
    assert any(bout in r.entites for r in e.relations.values())


def test_arc_aligne_refuse() -> None:
    e, outil = Esquisse(), OutilArc()
    outil.clic(Clic(Point2D(0, 0)))
    outil.clic(Clic(Point2D(20, 0)))
    modification = outil.clic(Clic(Point2D(10, 0)))
    assert modification is not None
    with pytest.raises(GeometrieImpossible):
        modification(e)


# --- Pièce, commandes et annulation ---


def test_creer_une_esquisse_et_annuler() -> None:
    piece, pile = Piece(), PileAnnulation()
    esquisse = Esquisse(piece.nom_esquisse_suivant(), "dessus")
    pile.executer(CommandeAjouterEsquisse(piece, esquisse))
    assert [e.nom for e in piece.esquisses] == ["Esquisse1"]
    assert piece.nom_esquisse_suivant() == "Esquisse2"
    pile.annuler()
    assert piece.esquisses == []


def test_chaque_trace_est_annulable() -> None:
    esquisse, pile = Esquisse(), PileAnnulation()
    pile.executer(CommandeEsquisse(esquisse, "Ligne", lambda e: e.ajouter_ligne((0, 0), (10, 0))))
    pile.executer(CommandeEsquisse(esquisse, "Cercle", lambda e: e.ajouter_cercle((0, 0), 5)))
    pile.annuler()
    assert [type(c).__name__ for c in esquisse.courbes()] == ["Ligne"]
    pile.annuler()
    assert esquisse.entites == {}
    pile.retablir()
    pile.retablir()
    assert len(esquisse.courbes()) == 2
    assert isinstance(esquisse["L1"], Ligne)


def test_trace_rate_ne_laisse_rien() -> None:
    esquisse, pile = Esquisse(), PileAnnulation()
    esquisse.ajouter_point(1, 1)
    with pytest.raises(GeometrieImpossible):
        pile.executer(
            CommandeEsquisse(esquisse, "Ligne", lambda e: e.ajouter_ligne((5, 5), (5, 5)))
        )
    assert [p.id for p in esquisse.points()] == ["P1"]
    assert not pile.peut_annuler


def test_esquisses_enregistrees_dans_le_fichier(tmp_path: object) -> None:
    from pathlib import Path

    document = Document(TypeDocument.PIECE, "Support")
    piece = document.modele
    assert isinstance(piece, Piece)
    esquisse = Esquisse("Esquisse1", "droite")
    esquisse.ajouter_rectangle(Point2D(0, 0), Point2D(40, 20))
    piece.esquisses.append(esquisse)
    chemin = Path(str(tmp_path)) / "Support.caop"
    format_natif.enregistrer(document, chemin)
    relu = format_natif.ouvrir(chemin)
    assert isinstance(relu.modele, Piece)
    assert relu.modele.vers_dict() == piece.vers_dict()
    assert relu.modele.esquisses[0].plan == "droite"
