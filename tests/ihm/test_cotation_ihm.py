"""Tests de l'étape 2.6 (interface) : outil Cote dans le mode esquisse, unités (COT-06).

Sans carte graphique : les entités sont désignées par leur identifiant
(`clic_entite_cote`) et la saisie de la valeur est simulée.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from cao.document.unites import UniteLongueur
from cao.esquisse.esquisse import Esquisse, GenreCote
from cao.esquisse.geometrie import Point2D
from cao.fichiers import format_natif
from cao.fichiers.types_documents import TypeDocument
from cao.ihm import textes
from cao.ihm.fenetre import FenetreDocument
from cao.ihm.mode_esquisse import ModeEsquisse
from cao.piece.piece import Piece


class Saisie:
    """Remplace la petite fenêtre de saisie : renvoie les réponses prévues, dans l'ordre."""

    def __init__(self) -> None:
        self.reponses: list[str | None] = []
        self.titres: list[str] = []

    def __call__(self, titre: str, proposee: str) -> str | None:
        self.titres.append(titre)
        return self.reponses.pop(0) if self.reponses else None


@pytest.fixture
def fenetre(application_qt: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[FenetreDocument]:
    monkeypatch.setattr(FenetreDocument, "choisir_plan", lambda self: "face")
    f = FenetreDocument(TypeDocument.PIECE, "Pièce1", avec_vue3d=False)
    f.show()
    yield f
    f.close()


def preparer(f: FenetreDocument) -> tuple[ModeEsquisse, Esquisse, Saisie]:
    """Rectangle tracé depuis l'origine, puis outil Cote actif."""
    f.executer_commande("esquisse_rectangle", "Rectangle")
    mode = f.mode_esquisse
    assert mode is not None
    mode.clic_plan(Point2D(0, 0))
    mode.clic_plan(Point2D(78, 31))
    saisie = Saisie()
    mode.demander_valeur = saisie
    f.executer_commande("esquisse_cote", "Cote")
    piece = f.document.modele
    assert isinstance(piece, Piece)
    return mode, piece.esquisses[0], saisie


def coter(mode: ModeEsquisse, *entites: str, curseur: Point2D | None = None) -> str | None:
    for entite in entites:
        mode.clic_entite_cote(entite)
    return mode.placer_cote(curseur)


def test_coter_un_rectangle_jusqu_a_le_contraindre(fenetre: FenetreDocument) -> None:
    mode, esquisse, saisie = preparer(fenetre)
    bas, droite = "L1", "L2"
    saisie.reponses = ["80", "30"]
    assert fenetre.statusBar().currentMessage() == textes.CONSIGNES_COTE[0]
    coter(mode, bas)
    coter(mode, droite)
    assert esquisse.longueur(bas) == pytest.approx(80)
    assert esquisse.longueur(droite) == pytest.approx(30)
    assert "totalement contrainte" in fenetre.pastilles[1].text()
    assert [c.genre for c in esquisse.cotes.values()] == [GenreCote.LONGUEUR] * 2
    assert "78,00 mm" in saisie.titres[0]  # la fenêtre montre la mesure actuelle
    assert mode.texte_cote(esquisse.cotes["D1"]) == "80,00 mm"


def test_saisie_annulee_garde_la_mesure(fenetre: FenetreDocument) -> None:
    mode, esquisse, saisie = preparer(fenetre)
    saisie.reponses = [None]
    coter(mode, "L1")
    assert esquisse.cotes["D1"].valeur == pytest.approx(78)


def test_annuler_la_valeur_puis_la_cote(fenetre: FenetreDocument) -> None:
    mode, esquisse, saisie = preparer(fenetre)
    saisie.reponses = ["100"]
    coter(mode, "L1")
    assert esquisse.longueur("L1") == pytest.approx(100)
    fenetre.action_annuler.trigger()  # Ctrl+Z : retour à la mesure posée
    assert esquisse.cotes["D1"].valeur == pytest.approx(78)
    fenetre.action_annuler.trigger()  # Ctrl+Z : la cote disparaît
    assert esquisse.cotes == {}


def test_cote_en_trop_devient_de_reference(fenetre: FenetreDocument) -> None:
    mode, esquisse, saisie = preparer(fenetre)
    saisie.reponses = ["80", "30"]
    coter(mode, "L1")
    coter(mode, "L2")
    en_trop = coter(mode, "L3")  # le haut : déjà déterminé par le bas
    assert en_trop is not None
    assert esquisse.cotes[en_trop].pilotee
    assert mode.texte_cote(esquisse.cotes[en_trop]) == "(80,00 mm)"
    assert fenetre.statusBar().currentMessage() == textes.COTE_DEVENUE_PILOTEE
    assert "totalement contrainte" in fenetre.pastilles[1].text()


def test_saisie_invalide_ou_impossible(fenetre: FenetreDocument) -> None:
    mode, esquisse, saisie = preparer(fenetre)
    saisie.reponses = ["abc"]
    coter(mode, "L1")
    assert "n'est pas un nombre" in fenetre.statusBar().currentMessage()
    assert esquisse.cotes["D1"].valeur == pytest.approx(78)
    saisie.reponses = ["-5"]
    mode.modifier_cote("D1")
    assert "strictement positive" in fenetre.statusBar().currentMessage()


def test_cercle_diametre_et_arc_rayon(fenetre: FenetreDocument) -> None:
    mode, esquisse, saisie = preparer(fenetre)
    c = esquisse.ajouter_cercle((40, 15), 5)
    a = esquisse.ajouter_arc((100, 0), (110, 0), (100, 10))
    saisie.reponses = ["12", "8"]
    d1 = coter(mode, c)
    d2 = coter(mode, a)
    assert d1 is not None and d2 is not None
    assert mode.texte_cote(esquisse.cotes[d1]) == "Ø 12,00 mm"
    assert mode.texte_cote(esquisse.cotes[d2]) == "R 8,00 mm"
    assert esquisse.rayon(c) == pytest.approx(6)
    assert esquisse.rayon(a) == pytest.approx(8)


def test_selection_impossible_affiche_l_aide(fenetre: FenetreDocument) -> None:
    mode, esquisse, _ = preparer(fenetre)
    point = esquisse.ajouter_point(10, 50)
    assert coter(mode, point) is None
    assert "sélectionnez" in fenetre.statusBar().currentMessage()


def test_cote_de_reference_non_modifiable(fenetre: FenetreDocument) -> None:
    mode, _esquisse, saisie = preparer(fenetre)
    saisie.reponses = ["80", "30"]
    coter(mode, "L1")
    coter(mode, "L2")
    en_trop = coter(mode, "L3")
    assert en_trop is not None
    mode.modifier_cote(en_trop)
    assert fenetre.statusBar().currentMessage() == textes.COTE_PILOTEE_NON_MODIFIABLE


def test_echap_vide_la_selection_puis_quitte_l_outil(fenetre: FenetreDocument) -> None:
    mode, _esquisse, _ = preparer(fenetre)
    mode.clic_entite_cote("L1")
    fenetre.action_echap.trigger()
    assert mode.selection_cote == [] and mode.cotation
    fenetre.action_echap.trigger()
    assert not mode.cotation and mode.actif


# --- Unités (COT-06) ---


def test_changer_d_unite_change_affichage_et_saisie(fenetre: FenetreDocument) -> None:
    mode, esquisse, saisie = preparer(fenetre)
    fenetre.actions_unites[UniteLongueur.CM].trigger()
    assert fenetre.bouton_unites.text() == "cm"
    saisie.reponses = ["5"]  # 5 cm
    coter(mode, "L1")
    assert esquisse.longueur("L1") == pytest.approx(50)
    assert mode.texte_cote(esquisse.cotes["D1"]) == "5,00 cm"
    fenetre.actions_decimales[0].trigger()
    assert mode.texte_cote(esquisse.cotes["D1"]) == "5 cm"


def test_changement_d_unite_annulable(fenetre: FenetreDocument) -> None:
    fenetre.actions_unites[UniteLongueur.POUCE].trigger()
    assert fenetre.document.unites.longueur == UniteLongueur.POUCE
    fenetre.action_annuler.trigger()
    assert fenetre.document.unites.longueur == UniteLongueur.MM
    assert fenetre.bouton_unites.text() == "mm"


def test_unites_enregistrees_dans_le_fichier(
    fenetre: FenetreDocument, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenetre.actions_unites[UniteLongueur.CM].trigger()
    fenetre.actions_decimales[1].trigger()
    monkeypatch.setattr(
        FenetreDocument, "choisir_chemin_enregistrement", lambda self: tmp_path / "Cm.caop"
    )
    assert fenetre.enregistrer()
    relu = format_natif.ouvrir(tmp_path / "Cm.caop")
    assert relu.unites.longueur == UniteLongueur.CM and relu.unites.decimales == 1


# --- Déroulement comme dans SolidWorks (demande de Simon) ---


def test_survol_met_en_evidence_la_ligne_ou_le_point(fenetre: FenetreDocument) -> None:
    mode, esquisse, _ = preparer(fenetre)
    mode.mouvement_cote(Point2D(39, 0.3), tolerance=1.0)  # sur la ligne du bas
    assert mode.survol == "L1"
    coin = esquisse["L1"].fin  # type: ignore[union-attr]
    mode.mouvement_cote(esquisse.position(coin), tolerance=1.0)  # sur le coin : le point prime
    assert mode.survol == coin
    mode.mouvement_cote(Point2D(39, 15), tolerance=1.0)  # dans le vide
    assert mode.survol is None


def test_la_cote_suit_la_souris_puis_se_place_au_clic(fenetre: FenetreDocument) -> None:
    mode, esquisse, saisie = preparer(fenetre)
    mode.clic_cote(Point2D(39, 0.2), tolerance=1.0)  # 1. clic sur la ligne du bas
    assert mode.selection_cote == ["L1"]
    mode.mouvement_cote(Point2D(39, -20), tolerance=1.0)  # 2. la souris descend
    assert mode.apercu_cote is not None
    assert mode.apercu_cote.valeur == pytest.approx(78)  # la valeur s'affiche déjà
    assert mode.apercu_cote.deport == pytest.approx(-20)  # et suit la souris
    saisie.reponses = ["80"]
    mode.clic_cote(
        Point2D(39, -20), tolerance=1.0
    )  # 3. clic dans le vide : placée, valeur demandée
    assert esquisse.cotes["D1"].deport == pytest.approx(-20)
    assert esquisse.longueur("L1") == pytest.approx(80)
    assert mode.apercu_cote is None and mode.selection_cote == []


def test_deux_entites_puis_placement(fenetre: FenetreDocument) -> None:
    mode, esquisse, saisie = preparer(fenetre)
    gauche, droite = esquisse["L4"], esquisse["L2"]
    mode.clic_cote(Point2D(0.2, 15), tolerance=1.0)  # ligne de gauche
    mode.clic_cote(Point2D(77.8, 15), tolerance=1.0)  # ligne de droite (parallèle)
    assert mode.selection_cote == [gauche.id, droite.id]
    mode.mouvement_cote(Point2D(39, 45), tolerance=1.0)
    assert mode.apercu_cote is not None and mode.apercu_cote.genre == GenreCote.DISTANCE
    saisie.reponses = ["60"]
    mode.clic_cote(Point2D(39, 45), tolerance=1.0)
    assert esquisse.longueur("L1") == pytest.approx(60)


def test_reclic_sur_une_entite_la_deselectionne(fenetre: FenetreDocument) -> None:
    mode, _esquisse, _ = preparer(fenetre)
    mode.clic_cote(Point2D(39, 0.2), tolerance=1.0)
    mode.clic_cote(Point2D(39, 0.2), tolerance=1.0)
    assert mode.selection_cote == []
