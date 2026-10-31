# CAO simplifiée

Modeleur 3D paramétrique simplifié, inspiré de SolidWorks : pièce, assemblage, mise en plan.
Logiciel libre (GPL 3), hors ligne, pour Windows et Linux.

## Installer l'environnement de développement

```bash
conda env create -f environment.yml
conda activate cao
pip install -e .
```

## Lancer

```bash
python -m cao
```

## Vérifier

```bash
pytest
ruff check .
mypy
```

Documents : [cahier des charges](docs/cahier_des_charges.md), [plan de développement](docs/plan_developpement.md), [architecture](docs/architecture.md), [avancement](PLAN.md).
