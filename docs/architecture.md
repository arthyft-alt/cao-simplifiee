# Architecture du logiciel

> Mis à jour à chaque lot. Dernière mise à jour : 2026-10-31 (étape 1.1).

## Principe

Trois couches, de haut en bas :

1. **Interface (`ihm`)** : fenêtres, ruban, arbre, vue 3D, panneaux. Seule couche qui utilise Qt (PySide6). Elle ne fait aucun calcul géométrique : elle transmet les demandes de l'utilisateur à la couche métier et affiche le résultat.
2. **Métier (`esquisse`, `piece`, `assemblage`, `plan`, `fichiers`)** : la logique de la CAO. Testable sans ouvrir de fenêtre.
3. **Noyau (`noyau`)** : enveloppe autour d'OpenCascade (pythonocc-core). C'est le seul endroit qui appelle `OCC.Core`, pour isoler cette bibliothèque énorme et peu documentée.

Le solveur d'esquisse (python-solvespace) est appelé uniquement par `esquisse`.

## Paquets

| Paquet | Rôle | Peut importer |
| --- | --- | --- |
| `cao.noyau` | Formes, booléens, congés, projection HLR, propriétés de masse | OCC.Core |
| `cao.esquisse` | Entités 2D, relations, cotes, degré de contrainte | python_solvespace, noyau |
| `cao.piece` | Fonctions volumiques, arbre de construction, reconstruction | noyau, esquisse |
| `cao.assemblage` | Composants, contraintes d'assemblage, interférences | noyau, piece |
| `cao.plan` | Vues, cotation, cartouche, nomenclature | noyau, piece, assemblage |
| `cao.fichiers` | Format natif, STEP, STL, DXF | noyau et paquets métier |
| `cao.ihm` | Tout ce qui est Qt, y compris le visualiseur `OCC.Display` | tous les paquets |

## Règles vérifiées automatiquement

Le fichier `tests/test_structure.py` échoue si l'une de ces règles est violée :

- `noyau`, `esquisse`, `piece`, `assemblage`, `plan` n'importent jamais PySide6 ni `OCC.Display`.
- Seul `noyau` importe `OCC.Core`.
- Seul `ihm` importe `OCC.Display`.

## Arborescence

```
src/cao/
├── __init__.py      version et nom de l'application
├── __main__.py      permet « python -m cao »
├── main.py          point d'entrée
├── noyau/  esquisse/  piece/  assemblage/  plan/  fichiers/
└── ihm/
    └── panneaux/
tests/               même découpage que src/cao
└── pieces_reference/  pièces de recette R1 à R8
prototypes/          scripts jetables de la phase 0 (hors logiciel)
```
