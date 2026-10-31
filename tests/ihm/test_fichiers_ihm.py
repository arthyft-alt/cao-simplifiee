"""Tests de l'étape 1.6 (interface) : enregistrer, ouvrir, fermer, sauvegarde automatique."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent

from cao.fichiers import format_natif, recuperation
from cao.fichiers.types_documents import TypeDocument
from cao.ihm import textes
from cao.ihm.fenetre import FenetreDocument
from cao.ihm.gestionnaire import GestionnaireDocuments


def supprimer_fenetres_fermees() -> None:
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture
def gestionnaire(application_qt: object, tmp_path: Path) -> Iterator[GestionnaireDocuments]:
    g = GestionnaireDocuments(avec_vue3d=False, dossier_recuperation=tmp_path / "recuperation")
    yield g
    g.tout_fermer()
    supprimer_fenetres_fermees()


def repondre_chemin(monkeypatch: pytest.MonkeyPatch, chemin: Path | None) -> None:
    monkeypatch.setattr(FenetreDocument, "choisir_chemin_enregistrement", lambda self: chemin)


# --- Enregistrer ---


def test_premier_enregistrement_demande_ou(
    gestionnaire: GestionnaireDocuments, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenetre = gestionnaire.ouvrir(TypeDocument.PIECE)
    fenetre.document.renommer("Brouillon")
    repondre_chemin(monkeypatch, tmp_path / "Équerre")  # sans extension : ajoutée seule
    assert fenetre.enregistrer()
    assert (tmp_path / "Équerre.caop").is_file()
    assert fenetre.nom_document == "Équerre"
    assert "Équerre" in fenetre.windowTitle()
    assert not fenetre.isWindowModified()
    assert fenetre.statusBar().currentMessage() == textes.message_enregistre("Équerre.caop")


def test_enregistrer_ensuite_ne_redemande_pas(
    gestionnaire: GestionnaireDocuments, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenetre = gestionnaire.ouvrir(TypeDocument.PIECE)
    repondre_chemin(monkeypatch, tmp_path / "Support.caop")
    fenetre.enregistrer()

    def ne_doit_pas_etre_appele(self: FenetreDocument) -> Path:
        raise AssertionError("Ctrl+S ne doit pas redemander le fichier")

    monkeypatch.setattr(FenetreDocument, "choisir_chemin_enregistrement", ne_doit_pas_etre_appele)
    fenetre.document.renommer("Support")  # nom identique : aucune modification
    fenetre.document.renommer("Autre")
    fenetre.action_enregistrer.trigger()
    assert not fenetre.isWindowModified()


def test_enregistrement_annule(
    gestionnaire: GestionnaireDocuments, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenetre = gestionnaire.ouvrir(TypeDocument.PIECE)
    repondre_chemin(monkeypatch, None)  # l'utilisateur ferme la fenêtre de choix
    assert not fenetre.enregistrer()
    assert fenetre.document.chemin is None


def test_erreur_d_ecriture_affichee(
    gestionnaire: GestionnaireDocuments, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenetre = gestionnaire.ouvrir(TypeDocument.PIECE)
    repondre_chemin(monkeypatch, tmp_path / "Pièce.caop")
    messages: list[str] = []
    monkeypatch.setattr(FenetreDocument, "afficher_erreur", lambda self, t, m: messages.append(m))

    def panne(*_arguments: object) -> None:
        raise OSError("disque plein (simulation)")

    monkeypatch.setattr(format_natif, "enregistrer", panne)
    assert not fenetre.enregistrer()
    assert messages == ["disque plein (simulation)"]


# --- Fermer un document modifié ---


def test_fermeture_annulee_garde_la_fenetre(
    gestionnaire: GestionnaireDocuments, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenetre = gestionnaire.ouvrir(TypeDocument.PIECE)
    fenetre.document.renommer("Travail")
    monkeypatch.setattr(FenetreDocument, "demander_avant_fermeture", lambda self: "annuler")
    assert not fenetre.close()
    assert fenetre.isVisible()
    monkeypatch.setattr(FenetreDocument, "demander_avant_fermeture", lambda self: "ignorer")


def test_fermeture_avec_enregistrement(
    gestionnaire: GestionnaireDocuments, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenetre = gestionnaire.ouvrir(TypeDocument.ASSEMBLAGE)
    fenetre.document.renommer("Bride")
    monkeypatch.setattr(FenetreDocument, "demander_avant_fermeture", lambda self: "enregistrer")
    repondre_chemin(monkeypatch, tmp_path / "Bride.caoa")
    assert fenetre.close()
    assert (tmp_path / "Bride.caoa").is_file()


def test_document_non_modifie_se_ferme_sans_question(
    gestionnaire: GestionnaireDocuments, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interdit(self: FenetreDocument) -> str:
        raise AssertionError("aucune question attendue")

    monkeypatch.setattr(FenetreDocument, "demander_avant_fermeture", interdit)
    assert gestionnaire.ouvrir(TypeDocument.PIECE).close()


# --- Ouvrir ---


def test_ouvrir_un_fichier_dans_la_bonne_fenetre(
    gestionnaire: GestionnaireDocuments, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = gestionnaire.ouvrir(TypeDocument.MISE_EN_PLAN)
    repondre_chemin(monkeypatch, tmp_path / "Plan équerre.caom")
    plan.enregistrer()
    plan.close()
    supprimer_fenetres_fermees()

    rouvert = gestionnaire.ouvrir_fichier(tmp_path / "Plan équerre.caom")
    assert rouvert is not None
    assert rouvert.type_document == TypeDocument.MISE_EN_PLAN
    assert rouvert.ruban.noms_onglets()[0] == "Disposition des vues"
    assert rouvert.nom_document == "Plan équerre"
    assert not rouvert.isWindowModified()
    # Déjà ouvert : on retrouve la même fenêtre au lieu d'en ouvrir une deuxième.
    assert gestionnaire.ouvrir_fichier(tmp_path / "Plan équerre.caom") is rouvert


def test_ouvrir_un_fichier_invalide_affiche_un_message(
    gestionnaire: GestionnaireDocuments, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    faux = tmp_path / "faux.caop"
    faux.write_text("pas un document", encoding="utf-8")
    messages: list[str] = []
    monkeypatch.setattr(
        GestionnaireDocuments, "afficher_erreur", lambda self, p, t, m: messages.append(m)
    )
    assert gestionnaire.ouvrir_fichier(faux) is None
    assert messages and "n'est pas un document" in messages[0]


def test_menu_ouvrir_passe_par_le_gestionnaire(
    gestionnaire: GestionnaireDocuments, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    piece = gestionnaire.ouvrir(TypeDocument.PIECE)
    repondre_chemin(monkeypatch, tmp_path / "Axe.caop")
    piece.enregistrer()
    piece.close()
    supprimer_fenetres_fermees()
    autre = gestionnaire.ouvrir(TypeDocument.PIECE)
    monkeypatch.setattr(
        GestionnaireDocuments, "choisir_fichier_a_ouvrir", lambda self, p: tmp_path / "Axe.caop"
    )
    autre.action_ouvrir.trigger()
    assert "Axe" in [f.nom_document for f in gestionnaire.fenetres]


# --- Sauvegarde automatique et récupération ---


def test_sauvegarde_automatique_des_documents_modifies(gestionnaire: GestionnaireDocuments) -> None:
    modifie = gestionnaire.ouvrir(TypeDocument.PIECE)
    modifie.document.renommer("En cours")
    gestionnaire.ouvrir(TypeDocument.ASSEMBLAGE)  # non modifié : pas de copie
    gestionnaire.sauvegarde_automatique()
    copies = recuperation.lister(gestionnaire.dossier_recuperation)
    assert [c.nom for c in copies] == ["En cours"]
    assert gestionnaire.minuterie.interval() == 5 * 60 * 1000


def test_fermeture_normale_efface_la_copie(gestionnaire: GestionnaireDocuments) -> None:
    fenetre = gestionnaire.ouvrir(TypeDocument.PIECE)
    fenetre.document.renommer("En cours")
    gestionnaire.sauvegarde_automatique()
    fenetre.close()  # « ne pas enregistrer » (réponse par défaut des tests)
    supprimer_fenetres_fermees()
    assert recuperation.lister(gestionnaire.dossier_recuperation) == []


def test_recuperation_au_lancement(
    application_qt: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dossier = tmp_path / "recuperation"
    premier = GestionnaireDocuments(avec_vue3d=False, dossier_recuperation=dossier)
    fenetre = premier.ouvrir(TypeDocument.PIECE)
    fenetre.document.renommer("Travail du matin")
    premier.sauvegarde_automatique()
    # Plantage simulé : la fenêtre disparaît sans passer par la fermeture normale.
    premier.fenetres.clear()
    fenetre.destroyed.disconnect()
    fenetre.hide()

    monkeypatch.setattr(GestionnaireDocuments, "demander_recuperation", lambda self, noms: True)
    second = GestionnaireDocuments(avec_vue3d=False, dossier_recuperation=dossier)
    assert second.proposer_recuperation() == 1
    recupere = second.fenetres[0]
    assert recupere.nom_document == "Travail du matin"
    assert recupere.isWindowModified()  # à enregistrer
    second.tout_fermer()
    supprimer_fenetres_fermees()
