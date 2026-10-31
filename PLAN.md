# Plan du projet

## Où en est-on ?

- **Date :** 2026-10-31
- **Phase en cours :** Phase 0 — Prototypes
- **Dernière étape validée :** 0.1 techniquement terminée (reste le premier commit, en attente du nom et de l'e-mail Git de Simon)
- **Prochaine étape :** premier commit, puis 0.2 (afficher une boîte OpenCascade dans une fenêtre Qt)

## Contexte

- Poste de Simon : Windows 10 Famille. Déjà installés : Git 2.56, VS Code 1.144, Python 3.15 (non utilisé pour le projet).
- Miniforge installé dans `C:\Users\simon\miniforge3` (conda 26.9).
- Environnement `cao` : Python 3.11.18, pythonocc-core 8.0.1, PySide6 6.11.2, python-solvespace 3.0.8, ruff 0.17.3, mypy 2.4.1, pytest. Recette dans `environment.yml`.
- VS Code : extensions Python, Pylance et Ruff installées ; `.vscode/settings.json` pointe vers l'environnement `cao`.
- Dépôt Git initialisé (branche `main`), aucun commit encore. Git n'a pas encore de nom ni d'e-mail d'auteur configurés.
- Pas d'ordinateur Linux pour l'instant : tests Linux plus tard (intégration continue GitHub, étape 1.7).

## Décisions

| Date | Décision | Raison |
| --- | --- | --- |
| 2026-10-31 | CLAUDE.md réécrit pour le projet CAO (l'ancien venait d'un projet GMAO) | Il parlait de cPanel et d'hébergeur, sans rapport avec la CAO |
| 2026-10-31 | Un seul fichier mémoire : PLAN.md (remplace docs/journal.md du plan de développement) | Éviter deux journaux |
| 2026-10-31 | Cahier des charges et plan copiés dans `docs/` | Structure prévue par le plan de développement |
| 2026-10-31 | Développement sous Windows d'abord, Linux plus tard | Seul matériel disponible |
| 2026-10-31 | Solveur d'esquisse : python-solvespace — PROVISOIRE | À confirmer selon le mode de diffusion (licence GPL 3) |

## Lots et avancement

| Lot | Contenu | Exigences | État |
| --- | --- | --- | --- |
| 0. Prototypes | Cube affiché, extrusion + STEP, solveur, vue HLR | — | En cours (0.1 faite, 0.2 à faire) |
| 1. Socle | Fenêtre, navigation 3D, arbre, fichiers | IHM, ARB, DOC (P1) | À faire |
| 2. Esquisse | Entités, relations, solveur, cotation | ESQ, GEO, OUT, REL, COT (P1) | À faire |
| 3. Fonctions | Extrusions, révolutions, congés, répétitions | VOL, HAB, REP, REF, PRO (P1) | À faire |
| 4. Assemblage | Insertion, contraintes, déplacement | ASM, CTR, ANA (P1) | À faire |
| 5. Mise en plan | Vues, coupes, cotation, nomenclature, PDF, STEP, STL | MEP, VUE, ANN, NOM, SOR, ECH (P1) | À faire |
| 6. Version 1.0 | Exigences P2, installeurs, aide, tests utilisateurs | P2 | À faire |

## Points ouverts restants

- Diffusion : usage interne gratuit, logiciel libre ou commercial ? (conditionne la licence)
- Solveur d'esquisse : python-solvespace (GPL 3) ou planegcs de FreeCAD (LGPL) ?
- Langue : français seul ou français + anglais en 1.0 ?
- Compte GitHub : à créer ou existant ? (utile à l'étape 1.7)

## Journal des séances

- **2026-10-31 :** lecture des documents, réécriture de CLAUDE.md, création de PLAN.md et du dossier docs/. Installation de Miniforge, création de l'environnement `cao`, vérification : import OCC + PySide6 + solvespace OK, boîte 100×50×20 créée. Dépôt Git initialisé.
