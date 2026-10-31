"""Tests de l'étape 1.5 (interface) : boutons Annuler / Rétablir, titre, renommage."""

from collections.abc import Iterator

import pytest

from cao.document.historique import Commande
from cao.fichiers.types_documents import TypeDocument
from cao.ihm import textes
from cao.ihm.fenetre import FenetreDocument


class Compter(Commande):
    def __init__(self, compteur: list[int]) -> None:
        self.compteur = compteur
        self.libelle = "Compter"

    def executer(self) -> None:
        self.compteur[0] += 1

    def annuler(self) -> None:
        self.compteur[0] -= 1


@pytest.fixture
def fenetre(application_qt: object) -> Iterator[FenetreDocument]:
    f = FenetreDocument(TypeDocument.PIECE, "Pièce1", avec_vue3d=False)
    f.show()
    yield f
    f.close()


def test_rien_a_annuler_au_depart(fenetre: FenetreDocument) -> None:
    assert not fenetre.action_annuler.isEnabled()
    assert not fenetre.action_retablir.isEnabled()
    assert not fenetre.isWindowModified()


def test_raccourcis(fenetre: FenetreDocument) -> None:
    assert fenetre.action_annuler.shortcut().toString() == "Ctrl+Z"
    assert "Ctrl+Y" in [s.toString() for s in fenetre.action_retablir.shortcuts()]
    assert fenetre.action_annuler in fenetre.actions()


def test_dix_actions_via_les_boutons(fenetre: FenetreDocument) -> None:
    compteur = [0]
    for _ in range(10):
        fenetre.document.historique.executer(Compter(compteur))
    assert fenetre.action_annuler.isEnabled()
    assert fenetre.isWindowModified()  # étoile dans le titre
    assert fenetre.action_annuler.toolTip().startswith("Annuler : Compter")
    for _ in range(10):
        fenetre.action_annuler.trigger()
    assert compteur == [0]
    assert not fenetre.action_annuler.isEnabled()
    assert not fenetre.isWindowModified()
    for _ in range(10):
        fenetre.action_retablir.trigger()
    assert compteur == [10]


def test_renommer_par_l_arbre_puis_annuler(fenetre: FenetreDocument) -> None:
    arbre = fenetre.panneau_gauche.arbre
    arbre.racine.setText(0, "Support moteur")  # comme une saisie après double-clic
    assert fenetre.nom_document == "Support moteur"
    assert "Support moteur" in fenetre.windowTitle()
    fenetre.action_annuler.trigger()
    assert fenetre.nom_document == "Pièce1"
    assert arbre.racine.text(0) == "Pièce1"
    assert "Pièce1" in fenetre.windowTitle()


def test_nom_refuse_remet_l_ancien(fenetre: FenetreDocument) -> None:
    arbre = fenetre.panneau_gauche.arbre
    arbre.racine.setText(0, "a/b")
    assert fenetre.nom_document == "Pièce1"
    assert arbre.racine.text(0) == "Pièce1"
    assert "interdits" in fenetre.statusBar().currentMessage()
    assert not fenetre.action_annuler.isEnabled()


def test_echec_d_annulation_ne_bloque_pas(fenetre: FenetreDocument) -> None:
    class Rebelle(Commande):
        libelle = "Rebelle"

        def executer(self) -> None:
            pass

        def annuler(self) -> None:
            raise RuntimeError("impossible d'annuler")

    fenetre.document.historique.executer(Rebelle())
    fenetre.action_annuler.trigger()  # ne doit pas lever d'erreur
    assert fenetre.statusBar().currentMessage() == "impossible d'annuler"


def test_info_bulle_rien_a_annuler() -> None:
    assert textes.info_annuler("") == textes.RIEN_A_ANNULER


def test_touches_ctrl_z_et_ctrl_y_reellement_appuyees(fenetre: FenetreDocument) -> None:
    """Régression : Ctrl+Y était déclaré deux fois, donc ambigu, et ne faisait rien."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    fenetre.activateWindow()
    QTest.qWaitForWindowActive(fenetre)
    fenetre.renommer_document("Support moteur")
    ctrl = Qt.KeyboardModifier.ControlModifier
    QTest.keyClick(fenetre, Qt.Key.Key_Z, ctrl)
    assert fenetre.nom_document == "Pièce1"
    QTest.keyClick(fenetre, Qt.Key.Key_Y, ctrl)
    assert fenetre.nom_document == "Support moteur"
    QTest.keyClick(fenetre, Qt.Key.Key_Z, ctrl)
    QTest.keyClick(fenetre, Qt.Key.Key_Z, ctrl | Qt.KeyboardModifier.ShiftModifier)
    assert fenetre.nom_document == "Support moteur"


def test_aucun_raccourci_en_double(fenetre: FenetreDocument) -> None:
    """Une même touche déclarée deux fois rend le raccourci inopérant."""
    from PySide6.QtGui import QAction

    vus: list[str] = []
    for action in fenetre.findChildren(QAction):  # toutes : menu, ruban, barre de vues
        for raccourci in action.shortcuts():
            vus.append(raccourci.toString())
    doublons = {r for r in vus if vus.count(r) > 1}
    assert not doublons, f"raccourcis en double : {doublons}"
