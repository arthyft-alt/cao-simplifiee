"""Tests de l'étape 1.1 : le squelette du projet et les règles d'architecture.

Les règles d'architecture de CLAUDE.md sont vérifiées automatiquement ici,
pour qu'un oubli soit détecté tout de suite :
    - les paquets de calcul n'importent jamais Qt ;
    - seul « noyau » importe OCC.Core (le moteur géométrique) ;
    - seul « ihm » importe OCC.Display (le visualiseur 3D, qui dépend de Qt).
"""

import ast
import importlib
from pathlib import Path

import pytest

import cao
from cao.main import texte_version

RACINE_SOURCES = Path(cao.__file__).parent
PAQUETS = ["noyau", "esquisse", "piece", "assemblage", "plan", "fichiers", "document", "ihm"]
PAQUETS_SANS_QT = ["noyau", "esquisse", "piece", "assemblage", "plan", "document"]


def modules_importes(paquet: str) -> set[str]:
    """Noms de tous les modules importés par les fichiers .py d'un paquet."""
    noms: set[str] = set()
    for fichier in (RACINE_SOURCES / paquet).rglob("*.py"):
        arbre = ast.parse(fichier.read_text(encoding="utf-8"))
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.Import):
                noms.update(alias.name for alias in noeud.names)
            elif isinstance(noeud, ast.ImportFrom) and noeud.module:
                noms.add(noeud.module)
    return noms


def test_version_affichee() -> None:
    assert texte_version() == f"CAO simplifiée {cao.__version__}"


@pytest.mark.parametrize("paquet", PAQUETS)
def test_paquet_importable(paquet: str) -> None:
    importlib.import_module(f"cao.{paquet}")


@pytest.mark.parametrize("paquet", PAQUETS_SANS_QT)
def test_calcul_sans_qt(paquet: str) -> None:
    interdits = {m for m in modules_importes(paquet) if m.split(".")[0] == "PySide6"}
    interdits |= {m for m in modules_importes(paquet) if m.startswith("OCC.Display")}
    assert not interdits, f"cao.{paquet} importe Qt : {interdits}"


@pytest.mark.parametrize("paquet", [p for p in PAQUETS if p != "noyau"])
def test_occ_core_seulement_dans_noyau(paquet: str) -> None:
    interdits = {m for m in modules_importes(paquet) if m.startswith("OCC.Core")}
    assert not interdits, f"cao.{paquet} doit passer par cao.noyau : {interdits}"


@pytest.mark.parametrize("paquet", [p for p in PAQUETS if p != "ihm"])
def test_occ_display_seulement_dans_ihm(paquet: str) -> None:
    interdits = {m for m in modules_importes(paquet) if m.startswith("OCC.Display")}
    assert not interdits, f"cao.{paquet} ne doit pas utiliser le visualiseur : {interdits}"
