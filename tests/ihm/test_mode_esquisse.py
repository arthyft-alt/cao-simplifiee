"""Tests de l'étape 2.4 (interface) : mode esquisse dans une fenêtre de pièce.

Sans carte graphique : les clics sont donnés directement en coordonnées du plan
(`clic_plan`), comme si la vue 3D les avait déjà convertis.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from cao.esquisse.esquisse import ORIGINE
from cao.esquisse.geometrie import Point2D
from cao.fichiers import format_natif
from cao.fichiers.types_documents import TypeDocument
from cao.ihm import textes
from cao.ihm.fenetre import FenetreDocument
from cao.ihm.mode_esquisse import ModeEsquisse
from cao.piece.piece import Piece


@pytest.fixture
def fenetre(application_qt: object, monkeypatch: pytest.MonkeyPatch) -> Iterator[FenetreDocument]:
    monkeypatch.setattr(FenetreDocument, "choisir_plan", lambda self: "face")
    f = FenetreDocument(TypeDocument.PIECE, "Pièce1", avec_vue3d=False)
    f.show()
    yield f
    f.close()


def mode(f: FenetreDocument) -> ModeEsquisse:
    assert f.mode_esquisse is not None
    return f.mode_esquisse


def piece(f: FenetreDocument) -> Piece:
    assert isinstance(f.document.modele, Piece)
    return f.document.modele


def test_bouton_esquisse_cree_une_esquisse(fenetre: FenetreDocument) -> None:
    fenetre.executer_commande("esquisse", "Esquisse")
    assert mode(fenetre).actif
    assert [e.nom for e in piece(fenetre).esquisses] == ["Esquisse1"]
    assert "Esquisse1" in fenetre.panneau_gauche.arbre.noms_elements()
    assert fenetre.barre_affichage is not None
    assert fenetre.action_quitter_esquisse.isVisible()
    assert fenetre.pastilles[1].text() == textes.esquisse_vide("Esquisse1")
    assert fenetre.statusBar().currentMessage() == textes.CONSIGNE_SANS_OUTIL


def test_plan_selectionne_dans_l_arbre(
    fenetre: FenetreDocument, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interdit(self: FenetreDocument) -> str:
        raise AssertionError("le plan sélectionné doit suffire")

    monkeypatch.setattr(FenetreDocument, "choisir_plan", interdit)
    arbre = fenetre.panneau_gauche.arbre
    enfants = [arbre.racine.child(i) for i in range(arbre.racine.childCount())]
    element = next(e for e in enfants if e is not None and e.text(0) == "Plan de dessus")
    arbre.setCurrentItem(element)
    fenetre.executer_commande("esquisse", "Esquisse")
    assert piece(fenetre).esquisses[0].plan == "dessus"


def test_choix_du_plan_annule(fenetre: FenetreDocument, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(FenetreDocument, "choisir_plan", lambda self: None)
    fenetre.executer_commande("esquisse_ligne", "Ligne")
    assert not mode(fenetre).actif
    assert piece(fenetre).esquisses == []


def test_tracer_un_rectangle_puis_annuler(fenetre: FenetreDocument) -> None:
    fenetre.executer_commande("esquisse_rectangle", "Rectangle")  # ouvre l'esquisse seul
    m = mode(fenetre)
    assert fenetre.statusBar().currentMessage() == textes.CONSIGNES_OUTILS["rectangle"][0]
    m.clic_plan(Point2D(0.2, 0.1))  # près de l'origine : accroché
    assert fenetre.statusBar().currentMessage() == textes.CONSIGNES_OUTILS["rectangle"][1]
    m.clic_plan(Point2D(80, 30))
    esquisse = piece(fenetre).esquisses[0]
    assert len(esquisse.courbes()) == 4
    assert any(ORIGINE in r.entites for r in esquisse.relations.values())
    assert "sous-contrainte" in fenetre.pastilles[1].text()
    assert fenetre.isWindowModified()

    fenetre.action_annuler.trigger()  # Ctrl+Z : le rectangle disparaît
    assert esquisse.courbes() == []
    assert m.actif
    fenetre.action_annuler.trigger()  # Ctrl+Z : l'esquisse elle-même disparaît
    assert piece(fenetre).esquisses == []
    assert not m.actif
    assert fenetre.pastilles[1].text() == textes.ETAT_PAS_D_ESQUISSE


def test_lignes_chainees_et_echap(fenetre: FenetreDocument) -> None:
    fenetre.executer_commande("esquisse_ligne", "Ligne")
    m = mode(fenetre)
    for x, y in [(0, 0), (50, 0), (50, 20)]:
        m.clic_plan(Point2D(x, y))
    assert len(piece(fenetre).esquisses[0].courbes()) == 2
    assert m.outil is not None and m.outil.en_cours
    fenetre.action_echap.trigger()  # 1er Échap : fin de la suite de lignes
    assert m.outil is not None and not m.outil.en_cours
    fenetre.action_echap.trigger()  # 2e Échap : plus d'outil
    assert m.outil is None and m.actif
    fenetre.action_echap.trigger()  # 3e Échap : on quitte l'esquisse
    assert not m.actif


def test_trace_impossible_affiche_un_message(fenetre: FenetreDocument) -> None:
    fenetre.executer_commande("esquisse_arc", "Arc")
    m = mode(fenetre)
    for x in (0, 20, 10):  # trois points alignés : pas d'arc
        m.clic_plan(Point2D(x, 5))
    assert "alignés" in fenetre.statusBar().currentMessage()
    assert piece(fenetre).esquisses[0].courbes() == []


def test_quitter_puis_rouvrir_depuis_l_arbre(fenetre: FenetreDocument) -> None:
    fenetre.executer_commande("esquisse_cercle", "Cercle")
    m = mode(fenetre)
    m.clic_plan(Point2D(0, 0))
    m.clic_plan(Point2D(10, 0))
    fenetre.action_quitter_esquisse.trigger()
    assert not m.actif
    fenetre.panneau_gauche.arbre.esquisse_ouverte.emit("Esquisse1")  # double-clic
    assert m.actif and m.esquisse is piece(fenetre).esquisses[0]
    assert len(piece(fenetre).esquisses) == 1  # pas de nouvelle esquisse


def test_supprimer_une_entite_est_annulable(fenetre: FenetreDocument) -> None:
    fenetre.executer_commande("esquisse_cercle", "Cercle")
    m = mode(fenetre)
    m.clic_plan(Point2D(0, 0))
    m.clic_plan(Point2D(10, 0))
    esquisse = piece(fenetre).esquisses[0]
    m.supprimer(["C1", ORIGINE])  # l'origine ne se supprime jamais
    assert esquisse.courbes() == []
    fenetre.action_annuler.trigger()
    assert len(esquisse.courbes()) == 1


def test_esquisse_enregistree_et_rouverte(
    fenetre: FenetreDocument, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenetre.executer_commande("esquisse_rectangle", "Rectangle")
    m = mode(fenetre)
    m.clic_plan(Point2D(0, 0))
    m.clic_plan(Point2D(40, 20))
    monkeypatch.setattr(
        FenetreDocument, "choisir_chemin_enregistrement", lambda self: tmp_path / "Cale.caop"
    )
    assert fenetre.enregistrer()
    rouverte = FenetreDocument(
        TypeDocument.PIECE, avec_vue3d=False, document=format_natif.ouvrir(tmp_path / "Cale.caop")
    )
    assert "Esquisse1" in rouverte.panneau_gauche.arbre.noms_elements()
    assert isinstance(rouverte.document.modele, Piece)
    assert len(rouverte.document.modele.esquisses[0].courbes()) == 4
    rouverte.close()


def test_raccourci_l_pour_la_ligne(fenetre: FenetreDocument) -> None:
    from PySide6.QtTest import QTest

    fenetre.activateWindow()
    QTest.qWaitForWindowActive(fenetre)
    QTest.keyClick(fenetre, Qt.Key.Key_L)
    m = mode(fenetre)
    assert m.actif and m.outil is not None and m.outil.nom == "ligne"


def test_pas_de_mode_esquisse_hors_piece(application_qt: object) -> None:
    f = FenetreDocument(TypeDocument.ASSEMBLAGE, "A1", avec_vue3d=False)
    assert f.mode_esquisse is None
    f.close()
