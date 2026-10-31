"""Tests DOC-01 : une fenêtre par document, choix du type à la création."""

from collections.abc import Iterator

import pytest

from cao.fichiers.types_documents import TypeDocument
from cao.ihm.gestionnaire import GestionnaireDocuments
from cao.ihm.nouveau_document import DialogueNouveauDocument


@pytest.fixture
def gestionnaire(application_qt: object) -> Iterator[GestionnaireDocuments]:
    g = GestionnaireDocuments(avec_vue3d=False)
    yield g
    g.tout_fermer()


def test_dialogue_propose_les_trois_types(application_qt: object) -> None:
    dialogue = DialogueNouveauDocument()
    assert [c.type_document for c in dialogue.cartes] == list(TypeDocument)


def test_clic_sur_une_carte_choisit_le_type(application_qt: object) -> None:
    dialogue = DialogueNouveauDocument()
    dialogue.cartes[1].click()
    assert dialogue.choix == TypeDocument.ASSEMBLAGE
    assert dialogue.result() == DialogueNouveauDocument.DialogCode.Accepted


def test_chaque_document_dans_sa_propre_fenetre(gestionnaire: GestionnaireDocuments) -> None:
    piece = gestionnaire.ouvrir(TypeDocument.PIECE)
    assemblage = gestionnaire.ouvrir(TypeDocument.ASSEMBLAGE)
    plan = gestionnaire.ouvrir(TypeDocument.MISE_EN_PLAN)
    assert len({id(piece), id(assemblage), id(plan)}) == 3
    assert [f.nom_document for f in gestionnaire.fenetres] == ["Pièce1", "Assemblage1", "Plan1"]


def test_numerotation_par_type(gestionnaire: GestionnaireDocuments) -> None:
    gestionnaire.ouvrir(TypeDocument.PIECE)
    gestionnaire.ouvrir(TypeDocument.ASSEMBLAGE)
    deuxieme = gestionnaire.ouvrir(TypeDocument.PIECE)
    assert deuxieme.nom_document == "Pièce2"


def test_fermer_une_fenetre_la_retire_de_la_liste(
    gestionnaire: GestionnaireDocuments, application_qt: object
) -> None:
    from PySide6.QtCore import QCoreApplication, QEvent

    piece = gestionnaire.ouvrir(TypeDocument.PIECE)
    gestionnaire.ouvrir(TypeDocument.ASSEMBLAGE)
    piece.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert [f.nom_document for f in gestionnaire.fenetres] == ["Assemblage1"]


def test_quitter_ferme_toutes_les_fenetres(gestionnaire: GestionnaireDocuments) -> None:
    gestionnaire.ouvrir(TypeDocument.PIECE)
    gestionnaire.ouvrir(TypeDocument.MISE_EN_PLAN)
    gestionnaire.fenetres[0].quitter_demande.emit()
    assert all(not f.isVisible() for f in gestionnaire.fenetres)
