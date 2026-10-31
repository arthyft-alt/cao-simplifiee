"""Tests de l'étape 1.5 : annuler / rétablir.

Critère du plan de développement : test automatique sur 10 actions.
"""

import pytest

from cao.document.document import Document, NomInvalide
from cao.document.historique import Commande, PileAnnulation
from cao.fichiers.types_documents import TypeDocument


class Ajouter(Commande):
    """Commande d'essai : ajoute un nombre à une liste."""

    def __init__(self, liste: list[int], valeur: int) -> None:
        self.liste, self.valeur = liste, valeur
        self.libelle = f"Ajouter {valeur}"

    def executer(self) -> None:
        self.liste.append(self.valeur)

    def annuler(self) -> None:
        self.liste.remove(self.valeur)


class Echoue(Commande):
    libelle = "Échoue"

    def __init__(self, a_l_execution: bool = True) -> None:
        self.a_l_execution = a_l_execution

    def executer(self) -> None:
        if self.a_l_execution:
            raise RuntimeError("échec volontaire")

    def annuler(self) -> None:
        raise RuntimeError("échec volontaire à l'annulation")


def test_dix_actions_annulees_puis_retablies() -> None:
    pile, liste = PileAnnulation(), []
    for i in range(10):
        pile.executer(Ajouter(liste, i))
    assert liste == list(range(10))

    for attendu in range(9, -1, -1):
        assert pile.libelle_annuler == f"Ajouter {attendu}"
        assert pile.annuler()
    assert liste == []
    assert not pile.peut_annuler
    assert not pile.annuler()  # plus rien à annuler

    for _ in range(10):
        assert pile.retablir()
    assert liste == list(range(10))
    assert not pile.peut_retablir
    assert not pile.retablir()


def test_nouvelle_action_efface_le_retablir() -> None:
    pile, liste = PileAnnulation(), []
    for i in range(3):
        pile.executer(Ajouter(liste, i))
    pile.annuler()
    assert pile.peut_retablir
    pile.executer(Ajouter(liste, 99))
    assert not pile.peut_retablir
    assert liste == [0, 1, 99]


def test_echec_a_l_execution_ne_change_rien() -> None:
    pile, liste = PileAnnulation(), []
    pile.executer(Ajouter(liste, 1))
    with pytest.raises(RuntimeError):
        pile.executer(Echoue())
    assert pile.libelle_annuler == "Ajouter 1"
    assert liste == [1]


def test_echec_a_l_annulation_garde_la_pile_coherente() -> None:
    pile = PileAnnulation()
    pile.executer(Echoue(a_l_execution=False))
    with pytest.raises(RuntimeError):
        pile.annuler()
    assert pile.peut_annuler  # la commande est toujours « faite »
    assert not pile.peut_retablir


def test_groupe_annule_en_un_seul_pas() -> None:
    pile, liste = PileAnnulation(), []
    with pile.groupe("Trois ajouts"):
        for i in range(3):
            pile.executer(Ajouter(liste, i))
    assert pile.libelle_annuler == "Trois ajouts"
    pile.annuler()
    assert liste == []
    pile.retablir()
    assert liste == [0, 1, 2]


def test_groupe_en_echec_defait_ce_qui_a_ete_fait() -> None:
    pile, liste = PileAnnulation(), []
    with pytest.raises(RuntimeError), pile.groupe("Raté"):
        pile.executer(Ajouter(liste, 1))
        pile.executer(Echoue())
    assert liste == []
    assert not pile.peut_annuler


def test_etat_modifie_et_enregistre() -> None:
    pile, liste = PileAnnulation(), []
    assert not pile.modifie
    pile.executer(Ajouter(liste, 1))
    assert pile.modifie
    pile.marquer_enregistre()
    assert not pile.modifie
    pile.annuler()
    assert pile.modifie  # différent de la version enregistrée
    pile.retablir()
    assert not pile.modifie  # revenu exactement à la version enregistrée


def test_etat_enregistre_perdu_apres_nouvelle_branche() -> None:
    pile, liste = PileAnnulation(), []
    pile.executer(Ajouter(liste, 1))
    pile.marquer_enregistre()
    pile.annuler()
    pile.executer(Ajouter(liste, 2))  # nouvelle branche : l'état enregistré n'existe plus
    pile.annuler()
    assert pile.modifie


def test_observateurs_prevenus() -> None:
    pile, liste, appels = PileAnnulation(), [], []
    pile.abonner(lambda: appels.append(1))
    pile.executer(Ajouter(liste, 1))
    pile.annuler()
    pile.retablir()
    assert len(appels) == 3


# --- Document ---


def test_renommer_le_document_est_annulable() -> None:
    document = Document(TypeDocument.PIECE, "Pièce1")
    document.renommer("  Support moteur ")
    assert document.nom == "Support moteur"
    assert document.historique.libelle_annuler == "Renommer en « Support moteur »"
    document.historique.annuler()
    assert document.nom == "Pièce1"
    document.historique.retablir()
    assert document.nom == "Support moteur"


def test_renommer_avec_le_meme_nom_ne_cree_pas_d_etape() -> None:
    document = Document(TypeDocument.PIECE, "Pièce1")
    document.renommer("Pièce1")
    assert not document.historique.peut_annuler


@pytest.mark.parametrize("nom", ["", "   ", "a/b", "plan:1", "x?"])
def test_noms_refuses(nom: str) -> None:
    document = Document(TypeDocument.PIECE, "Pièce1")
    with pytest.raises(NomInvalide):
        document.renommer(nom)
    assert document.nom == "Pièce1"
