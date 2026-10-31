"""Tests de l'étape 1.3 (partie interface) : les boutons de vue et de rendu sont branchés."""

from collections.abc import Iterator

import pytest

from cao.fichiers.types_documents import TypeDocument
from cao.ihm import textes
from cao.ihm.fenetre import FenetreDocument
from cao.noyau.affichage import FiltreSelection, ModeRendu, VueStandard


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

    def changer_filtre(self, filtre: FiltreSelection) -> None:
        self.appels.append(("filtre", filtre))

    def vue_normale(self) -> bool:
        self.appels.append(("normale", None))
        return self.face_plane_selectionnee

    face_plane_selectionnee = False


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
        "Normale à": "Ctrl+8",
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


# --- Étape 1.4 : sélection, filtre, mesure rapide ---


def _aretes_d_une_boite() -> list[object]:
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCC.Core.TopAbs import TopAbs_EDGE
    from OCC.Core.TopExp import TopExp_Explorer

    explorateur = TopExp_Explorer(BRepPrimAPI_MakeBox(100.0, 50.0, 20.0).Shape(), TopAbs_EDGE)
    aretes = []
    while explorateur.More():
        aretes.append(explorateur.Current())
        explorateur.Next()
    return aretes


def test_filtre_de_selection(fenetre_et_vue: tuple[FenetreDocument, VueFactice]) -> None:
    fenetre, vue = fenetre_et_vue
    assert fenetre.barre_affichage is not None
    arete = next(a for a in fenetre.barre_affichage.actions_filtre if a.text() == "Arêtes")
    arete.trigger()
    assert vue.appels == [("filtre", FiltreSelection.ARETES)]
    assert arete.isChecked()


def test_normale_sans_face_plane_affiche_un_message(
    fenetre_et_vue: tuple[FenetreDocument, VueFactice],
) -> None:
    fenetre, vue = fenetre_et_vue
    fenetre.executer_commande("vue_normale", "Normale à")
    assert vue.appels == [("normale", None)]
    assert fenetre.statusBar().currentMessage() == textes.VUE_NORMALE_IMPOSSIBLE


def test_mesure_rapide_dans_la_barre_d_etat(
    fenetre_et_vue: tuple[FenetreDocument, VueFactice],
) -> None:
    fenetre, _ = fenetre_et_vue
    fenetre.show()
    arete_100 = next(a for a in _aretes_d_une_boite() if round(_longueur(a)) == 100)
    fenetre.selection_changee([arete_100])
    assert fenetre.pastille_mesure.isVisible()
    assert fenetre.pastille_mesure.text() == "Longueur : 100,00 mm"
    fenetre.selection_changee([])
    assert not fenetre.pastille_mesure.isVisible()


def test_bouton_mesurer_ouvre_le_panneau(
    fenetre_et_vue: tuple[FenetreDocument, VueFactice],
) -> None:
    fenetre, _ = fenetre_et_vue
    fenetre.executer_commande("mesurer", "Mesurer")
    assert fenetre.panneau_gauche.montre_mesure()
    aretes = _aretes_d_une_boite()
    fenetre.selection_changee(aretes[:2])
    assert "Distance" in fenetre.panneau_gauche.mesure.texte()
    fenetre.selection_changee(aretes[:3])
    assert fenetre.panneau_gauche.mesure.texte() == textes.MESURE_RIEN


def test_fermer_le_panneau_de_mesure_rend_l_arbre(
    fenetre_et_vue: tuple[FenetreDocument, VueFactice],
) -> None:
    fenetre, _ = fenetre_et_vue
    fenetre.executer_commande("mesurer", "Mesurer")
    fenetre.panneau_gauche.mesure.fermer_demande.emit()
    assert fenetre.panneau_gauche.montre_arbre()


def _longueur(arete: object) -> float:
    from cao.noyau.mesure import mesurer

    return next(v.valeur for v in mesurer([arete]) if v.nom == "Longueur")  # type: ignore[list-item]
