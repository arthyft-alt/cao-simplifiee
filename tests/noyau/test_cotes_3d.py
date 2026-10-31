"""Construction des cotes dessinées (OpenCascade), pour chaque genre de cote.

Ne demande pas de carte graphique : on vérifie que chaque cote se construit et
porte le bon texte (une erreur d'appel d'OpenCascade serait détectée ici).
"""

import pytest
from OCC.Core.PrsDim import PrsDim_Dimension

from cao.esquisse.esquisse import ORIGINE, Esquisse, GenreCote
from cao.esquisse.geometrie import Point2D
from cao.noyau.cotes_3d import creer_dimension


@pytest.fixture
def esquisse() -> Esquisse:
    e = Esquisse("Esquisse1", "dessus")
    e.ajouter_rectangle(Point2D(0, 0), Point2D(80, 30))  # L1 à L4
    e.ajouter_ligne((0, 0), (40, 50))  # L5, inclinée
    e.ajouter_cercle((40, 15), 5)  # C1
    e.ajouter_arc((100, 0), (110, 0), (100, 10))  # A1
    e.ajouter_point(20, 40)
    return e


@pytest.mark.parametrize(
    ("genre", "entites"),
    [
        (GenreCote.LONGUEUR, ["L1"]),
        (GenreCote.HORIZONTALE, ["L5"]),
        (GenreCote.VERTICALE, ["L5"]),
        (GenreCote.LONGUEUR, [ORIGINE, "P5"]),
        (GenreCote.DISTANCE, ["L1", "L3"]),
        (GenreCote.ANGLE, ["L1", "L5"]),
        (GenreCote.DIAMETRE, ["C1"]),
        (GenreCote.RAYON, ["A1"]),
    ],
)
def test_chaque_genre_de_cote_se_dessine(
    esquisse: Esquisse, genre: GenreCote, entites: list[str]
) -> None:
    identifiant = esquisse.ajouter_cote(genre, *entites)
    dimension = creer_dimension(esquisse, esquisse.cotes[identifiant], "12,34 mm")
    assert isinstance(dimension, PrsDim_Dimension)


def test_distance_point_ligne(esquisse: Esquisse) -> None:
    p = esquisse.ajouter_point(30, 60)
    identifiant = esquisse.ajouter_cote(GenreCote.DISTANCE, p, "L3")
    assert isinstance(creer_dimension(esquisse, esquisse.cotes[identifiant], "x"), PrsDim_Dimension)
