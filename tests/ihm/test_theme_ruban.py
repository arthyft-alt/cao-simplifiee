"""Tests des règles d'adaptation à l'écran et des icônes."""

import pytest
from PySide6.QtCore import QByteArray
from PySide6.QtSvg import QSvgRenderer

from cao.ihm import textes
from cao.ihm.icones import DESSINS, svg
from cao.ihm.ruban import choisir_mode
from cao.ihm.theme import taille_police_pour_ecran


@pytest.mark.parametrize(
    ("hauteur", "attendu"),
    [(728, 9), (768, 9), (1032, 10), (1400, 11)],
)
def test_taille_police_selon_ecran(hauteur: int, attendu: int) -> None:
    assert taille_police_pour_ecran(hauteur) == attendu


def test_choisir_mode_prend_le_plus_grand_qui_tient() -> None:
    largeurs = [("grand", 900), ("moyen", 700), ("compact", 400)]
    assert choisir_mode(largeurs, 1000) == "grand"
    assert choisir_mode(largeurs, 800) == "moyen"
    assert choisir_mode(largeurs, 500) == "compact"
    assert choisir_mode(largeurs, 100) == "compact"  # rien ne tient : le plus petit


@pytest.mark.parametrize("nom", sorted(DESSINS))
def test_icone_svg_valide(application_qt: object, nom: str) -> None:
    rendu = QSvgRenderer(QByteArray(svg(nom, "#000000", "#cccccc").encode("utf-8")))
    assert rendu.isValid(), f"icône {nom} invalide"


def test_toutes_les_icones_utilisees_existent() -> None:
    utilisees = {
        o.icone
        for onglets in textes.ONGLETS_PAR_TYPE.values()
        for onglet in onglets
        for g in onglet.groupes
        for o in g.outils
    }
    utilisees |= {o.icone for o in textes.BARRE_AFFICHAGE}
    assert utilisees <= set(DESSINS), f"icônes manquantes : {utilisees - set(DESSINS)}"
