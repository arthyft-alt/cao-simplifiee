"""Réglages communs à tous les tests.

Les tests d'interface tournent sans afficher de fenêtre à l'écran
(plateforme Qt « offscreen »), ce qui permet aussi de les lancer en
intégration continue, sur un serveur sans écran.
"""

import os
from collections.abc import Iterator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def application_qt() -> Iterator[object]:
    """Une seule application Qt pour toute la séance de tests."""
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture(autouse=True)
def dialogues_sans_attente(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aucune fenêtre de dialogue ne doit attendre une réponse pendant les tests.

    Par défaut : fermer sans enregistrer, ne rien choisir dans les sélecteurs de
    fichiers, ne pas récupérer, et lever une erreur si un message d'erreur
    inattendu devait s'afficher. Un test peut remplacer ces réponses.
    """
    from cao.ihm.fenetre import FenetreDocument
    from cao.ihm.gestionnaire import GestionnaireDocuments

    def erreur_inattendue(*arguments: object) -> None:
        raise AssertionError(f"message d'erreur inattendu : {arguments[-2:]}")

    monkeypatch.setattr(FenetreDocument, "demander_avant_fermeture", lambda self: "ignorer")
    monkeypatch.setattr(FenetreDocument, "choisir_chemin_enregistrement", lambda self: None)
    monkeypatch.setattr(FenetreDocument, "afficher_erreur", erreur_inattendue)
    monkeypatch.setattr(FenetreDocument, "choisir_plan", lambda self: None)
    monkeypatch.setattr(FenetreDocument, "demander_valeur_cote", lambda self, t, v: None)
    monkeypatch.setattr(GestionnaireDocuments, "choisir_fichier_a_ouvrir", lambda self, p: None)
    monkeypatch.setattr(GestionnaireDocuments, "demander_recuperation", lambda self, noms: False)
    monkeypatch.setattr(GestionnaireDocuments, "afficher_erreur", erreur_inattendue)
