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
