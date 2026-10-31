"""Tests DOC-01 : trois types de documents distincts."""

from cao.fichiers.types_documents import INFOS, CompteurDocuments, TypeDocument


def test_trois_types_de_documents() -> None:
    assert [t.value for t in TypeDocument] == ["piece", "assemblage", "mise_en_plan"]


def test_chaque_type_a_sa_propre_extension() -> None:
    extensions = [INFOS[t].extension for t in TypeDocument]
    assert len(set(extensions)) == 3


def test_seule_la_mise_en_plan_est_en_2d() -> None:
    assert INFOS[TypeDocument.PIECE].vue_3d
    assert INFOS[TypeDocument.ASSEMBLAGE].vue_3d
    assert not INFOS[TypeDocument.MISE_EN_PLAN].vue_3d


def test_numerotation_separee_par_type() -> None:
    compteur = CompteurDocuments()
    assert compteur.nom_suivant(TypeDocument.PIECE) == "Pièce1"
    assert compteur.nom_suivant(TypeDocument.PIECE) == "Pièce2"
    assert compteur.nom_suivant(TypeDocument.ASSEMBLAGE) == "Assemblage1"
    assert compteur.nom_suivant(TypeDocument.MISE_EN_PLAN) == "Plan1"
    assert compteur.nom_suivant(TypeDocument.PIECE) == "Pièce3"
