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

Sous Windows : **double-cliquer sur `lancer_cao.bat`** (il utilise toujours le Python de
l'environnement `cao`). On peut aussi glisser un document `.caop`, `.caoa` ou `.caom` sur ce fichier.

Depuis un terminal où l'environnement est activé (`conda activate cao`) :

```bash
python -m cao
python -m cao chemin/vers/document.caop
```

Attention : le Python « du système » (3.15 sur le poste de développement) ne connaît pas le
logiciel et répond `No module named cao`.

## Vérifier

```bash
pytest
ruff check .
mypy
```

Documents : [cahier des charges](docs/cahier_des_charges.md), [plan de développement](docs/plan_developpement.md), [architecture](docs/architecture.md), [avancement](PLAN.md).
