"""Tests de l'étape 1.3 (partie interface) : les boutons de vue et de rendu sont branchés."""

from collections.abc import Iterator

import pytest

from cao.fichiers.types_documents import TypeDocument
from cao.ihm import textes
from cao.ihm.fenetre import FenetreDocument
from cao.noyau.affichage import ModeRendu, VueStandard


class VueFactice:
    """Remplace la vue 3D (qui demande une carte graphique) et note les appels reçus."""

    def __init__(self) -> None:
        self.appels: list[tuple[str, object]] = []

    def orienter(self, vue_standard: VueStandard) -> None:
        self.appels.append(("orienter", vue_standard))

    def ajuster(self) -> None:
        self.appels.append(("ajuster", None))

    def changer_mode_rendu(self, mode: ModeRendu) -> None:
        self.appels.append(("rendu", mode))


@pytest.fixture
def fenetre_et_vue(application_qt: object) -> Iterator[tuple[FenetreDocument, VueFactice]]:
    fenetre = FenetreDocument(TypeDocument.PIECE, "Pièce1", avec_vue3d=False)
    vue = VueFactice()
    fenetre.brancher_commandes_vue(vue)
    yield fenetre, vue
    fenetre.close()


def test_bouton_face_oriente_la_vue(fenetre_et_vue: tuple[FenetreDocument, VueFactice]) -> None:
    fenetre, vue = fenetre_et_vue
    assert fenetre.barre_affichage is not None
    action = next(a for a in fenetre.barre_affichage.actions_vues() if a.text() == "Face")
    action.trigger()
    assert vue.appels == [("orienter", VueStandard.FACE)]


def test_raccourcis_des_vues_comme_solidworks(
    fenetre_et_vue: tuple[FenetreDocument, VueFactice],
) -> None:
    fenetre, _ = fenetre_et_vue
    assert fenetre.barre_affichage is not None
    raccourcis = {a.text(): a.shortcut().toString() for a in fenetre.barre_affichage.actions_vues()}
    assert raccourcis == {
        "Isométrique": "Ctrl+7",
        "Face": "Ctrl+1",
        "Dessus": "Ctrl+5",
        "Droite": "Ctrl+4",
        "Ajuster": "F",
    }


def test_toutes_les_commandes_d_affichage_sont_branchees(
    fenetre_et_vue: tuple[FenetreDocument, VueFactice],
) -> None:
    fenetre, _ = fenetre_et_vue
    onglet_affichage = next(
        o for o in textes.ONGLETS_PAR_TYPE[TypeDocument.PIECE] if o.nom == "Affichage"
    )
    outils = [o for g in onglet_affichage.groupes for o in g.outils] + textes.BARRE_AFFICHAGE
    for outil in outils:
        assert outil.commande in fenetre.commandes, f"{outil.nom} n'est pas branché"


def test_modes_de_rendu(fenetre_et_vue: tuple[FenetreDocument, VueFactice]) -> None:
    fenetre, vue = fenetre_et_vue
    fenetre.executer_commande("rendu_filaire", "Filaire")
    fenetre.executer_commande("rendu_lignes_cachees", "Lignes cachées")
    assert vue.appels == [("rendu", ModeRendu.FILAIRE), ("rendu", ModeRendu.LIGNES_CACHEES)]


def test_commande_inconnue_annonce_bientot(
    fenetre_et_vue: tuple[FenetreDocument, VueFactice],
) -> None:
    fenetre, vue = fenetre_et_vue
    fenetre.executer_commande("", "Ligne")
    assert vue.appels == []
    assert fenetre.statusBar().currentMessage() == textes.message_bientot("Ligne")
