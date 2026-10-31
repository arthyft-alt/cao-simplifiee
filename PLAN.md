# Plan du projet

## Où en est-on ?

- **Date :** 2026-10-31
- **Phase en cours :** Lot 1 — Socle
- **Dernière étape validée :** 1.1 — squelette `src/cao`, pyproject.toml, 25 tests verts, ruff et mypy (strict) sans erreur
- **Prochaine étape :** 1.2 (fenêtre principale : ruban à onglets, arbre à gauche, zone 3D, barre d'état — cahier des charges §2.2)

## Contexte

- Poste de Simon : Windows 10 Famille. Déjà installés : Git 2.56, VS Code 1.144, Python 3.15 (non utilisé pour le projet).
- Miniforge installé dans `C:\Users\simon\miniforge3` (conda 26.9).
- Environnement `cao` : Python 3.11.18, pythonocc-core 8.0.1, PySide6 6.11.2, python-solvespace 3.0.8, ruff 0.17.3, mypy 2.4.1, pytest. Recette dans `environment.yml`.
- VS Code : extensions Python, Pylance et Ruff installées ; `.vscode/settings.json` pointe vers l'environnement `cao`.
- Dépôt Git initialisé (branche `main`). Auteur Git : Simon (adresse anonyme GitHub : 250698513+arthyft-alt@users.noreply.github.com).
- Carte graphique : Intel HD Graphics 530, OpenGL 4.4 : l'affichage OpenCascade fonctionne.
- Pas d'ordinateur Linux pour l'instant : tests Linux plus tard (intégration continue GitHub, étape 1.7).

## Décisions

| Date | Décision | Raison |
| --- | --- | --- |
| 2026-10-31 | CLAUDE.md réécrit pour le projet CAO (l'ancien venait d'un projet GMAO) | Il parlait de cPanel et d'hébergeur, sans rapport avec la CAO |
| 2026-10-31 | Un seul fichier mémoire : PLAN.md (remplace docs/journal.md du plan de développement) | Éviter deux journaux |
| 2026-10-31 | Cahier des charges et plan copiés dans `docs/` | Structure prévue par le plan de développement |
| 2026-10-31 | Développement sous Windows d'abord, Linux plus tard | Seul matériel disponible |
| 2026-10-31 | Diffusion : logiciel libre et gratuit, licence GPL 3 ou ultérieure (fichier LICENSE) | Choix de Simon (1A) ; compatible avec python-solvespace |
| 2026-10-31 | Solveur d'esquisse : python-solvespace | Choix de Simon (2A) ; testé en phase 0 |
| 2026-10-31 | Langue : français seul en 1.0, textes externalisés pour traduction | Choix de Simon (3A) ; conforme à IHM-09 |
| 2026-10-31 | Les règles d'import de l'architecture sont vérifiées par un test automatique | Détecter tout de suite un import de Qt ou d'OCC au mauvais endroit |

## Lots et avancement

| Lot | Contenu | Exigences | État |
| --- | --- | --- | --- |
| 0. Prototypes | Cube affiché, extrusion + STEP, solveur, vue HLR | — | Terminé (2026-10-31) |
| 1. Socle | Fenêtre, navigation 3D, arbre, fichiers | IHM, ARB, DOC (P1) | En cours (1.1 faite) |
| 2. Esquisse | Entités, relations, solveur, cotation | ESQ, GEO, OUT, REL, COT (P1) | À faire |
| 3. Fonctions | Extrusions, révolutions, congés, répétitions | VOL, HAB, REP, REF, PRO (P1) | À faire |
| 4. Assemblage | Insertion, contraintes, déplacement | ASM, CTR, ANA (P1) | À faire |
| 5. Mise en plan | Vues, coupes, cotation, nomenclature, PDF, STEP, STL | MEP, VUE, ANN, NOM, SOR, ECH (P1) | À faire |
| 6. Version 1.0 | Exigences P2, installeurs, aide, tests utilisateurs | P2 | À faire |

## Points ouverts restants

- Compte GitHub : à créer ou existant ? (utile à l'étape 1.7)

## Journal des séances

- **2026-10-31 :** lecture des documents, réécriture de CLAUDE.md, création de PLAN.md et du dossier docs/. Installation de Miniforge, création de l'environnement `cao`, vérification : import OCC + PySide6 + solvespace OK, boîte 100×50×20 créée. Dépôt Git initialisé, premier commit. Décision : documents d'origine laissés à la racine. Prototype 0.2 écrit et lancé automatiquement sans erreur ; navigation façon SolidWorks (molette = rotation, Ctrl + molette = panoramique). 0.2 validée par Simon et commitée. Prototype 0.3 : plaque 100×50×20 percée Ø10, export STEP, volumes conformes ; ouvert dans FreeCAD par Simon, commité. Prototype 0.4 : rectangle contraint résolu exactement par python-solvespace (0 degré de liberté ; 1 sans la cote de hauteur), commité. Prototype 0.5 : vue de face HLR, arêtes vues en continu fort et cachées en interrompu fin ; note : HLR classe aussi en cachées les arêtes arrière superposées aux arêtes vues, à masquer sous le trait vu en mise en plan. 0.5 validée visuellement par Simon, commitée. Phase 0 terminée. Décisions : GPL 3, python-solvespace, français seul. Étape 1.1 : squelette du logiciel, pyproject.toml, README, LICENSE, docs/architecture.md, tests d'architecture (vérifiés : une faute volontaire est bien détectée).
