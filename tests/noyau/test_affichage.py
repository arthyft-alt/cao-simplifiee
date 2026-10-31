"""Tests de l'étape 1.3 (partie noyau) : orientations, cube de vue, modes de rendu.

Ce qui demande une carte graphique (zoom, clic sur le cube, rendu) a été vérifié
par un essai réel le 2026-10-31 : voir PLAN.md, journal de l'étape 1.3.
"""

from OCC.Core.AIS import AIS_ViewCube
from OCC.Core.V3d import V3d_Ypos, V3d_Zpos

from cao.noyau.affichage import (
    ETIQUETTES_CUBE,
    ORIENTATIONS,
    PAS_ROTATION_CLAVIER,
    ModeRendu,
    VueStandard,
    creer_cube_de_vue,
)


def test_chaque_vue_standard_a_une_orientation() -> None:
    assert set(ORIENTATIONS) == set(VueStandard)


def test_convention_y_vers_le_haut_comme_solidworks() -> None:
    # Vue de face : on regarde depuis +Z (plan XY) ; vue de dessus : depuis +Y.
    assert ORIENTATIONS[VueStandard.FACE] == V3d_Zpos
    assert ORIENTATIONS[VueStandard.DESSUS] == V3d_Ypos


def test_cube_a_six_faces_nommees_en_francais() -> None:
    assert sorted(ETIQUETTES_CUBE.values()) == sorted(
        ["Face", "Arrière", "Droite", "Gauche", "Dessus", "Dessous"]
    )


def test_creation_du_cube_de_vue() -> None:
    assert isinstance(creer_cube_de_vue(), AIS_ViewCube)


def test_quatre_modes_de_rendu() -> None:
    assert [m.value for m in ModeRendu] == ["ombre_aretes", "ombre", "filaire", "lignes_cachees"]


def test_rotation_clavier_de_15_degres() -> None:
    assert round(PAS_ROTATION_CLAVIER, 6) == round(15 * 3.141592653589793 / 180, 6)
