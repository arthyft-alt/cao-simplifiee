# Plan du projet

## Où en est-on ?

- **Date :** 2026-10-31
- **Dernière étape validée :** 1.6 — enregistrer / ouvrir / sauvegarde automatique / récupération ; lanceur `lancer_cao.bat` ; validée par Simon
- **Étape reportée :** 1.7 — intégration continue : recette `.github/workflows/tests.yml` écrite mais jamais exécutée ; reportée à la demande de Simon (pas encore de compte GitHub). À reprendre : compte GitHub, e-mail anonyme dans l'historique, dépôt public, envoi, badges verts.
- **Phase en cours :** Lot 2 — Esquisse
- **Dernière étape faite :** 2.2 — relations (REL-01 à 05) et solveur : 11 relations, degrés de liberté, conflits désignés ; un test par relation (24 tests)
- **Prochaine étape :** 2.3 (cotes et degré de contrainte sous / totalement / sur-contraint — COT-01, ESQ-07 ; tests sur 5 esquisses types)

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
| 2026-10-31 | Interface modernisée : style Fusion + thème clair (couleurs dans `ihm/theme.py`), icônes SVG maison, outils groupés par familles | Simon trouvait la première version « années 2000 » |
| 2026-10-31 | Ruban adaptatif : grand / moyen / compact selon la largeur ; pas de « grand » si l'écran fait moins de 800 px de haut ; police 9 / 10 / 11 pt selon la hauteur d'écran | Demande de Simon : boutons adaptés à la taille de l'écran |
| 2026-10-31 | Pièce, assemblage et mise en plan = 3 documents distincts, chacun dans sa propre fenêtre avec son ruban (pièce : Esquisse/Fonctions/Évaluer/Affichage ; assemblage : Assemblage/Évaluer/Affichage ; plan : Disposition des vues/Annotation/Esquisse, feuille 2D). Choix du type au lancement et par Fichier > Nouveau (Ctrl+N) | Demande de Simon, comme SolidWorks ; exigence DOC-01 |
| 2026-10-31 | Barre du haut amincie (166 → 74 px) : pas de barre de menus, bouton Fichier et recherche sur la ligne des onglets ; outils sur une ligne, icône + nom côte à côte ; pas de légendes de groupes | Simon : la barre du haut prenait trop de place |
| 2026-10-31 | Vue 3D libérée à la fermeture de la fenêtre (`Vue3D.liberer`) | Supprime l'erreur OpenGL « wglMakeCurrent() has failed » à la fermeture |
| 2026-10-31 | Convention d'axes : Y vers le haut, comme SolidWorks (plan de face = XY, dessus = XZ, droite = YZ) | Les élèves retrouvent les repères de SolidWorks |
| 2026-10-31 | Navigation : molette = rotation, Ctrl + molette = panoramique, molette = zoom au curseur, flèches = rotation 15°, F = ajuster ; bouton gauche = sélection seulement ; raccourcis de vues Ctrl+1/4/5/7 | Comme SolidWorks ; flèches utiles sur pavé tactile |
| 2026-10-31 | La vue 3D convertit les positions de souris en pixels réels (facteur d'agrandissement Windows, 1,25 chez Simon) | pythonocc ne le fait pas : clics décalés sinon |
| 2026-10-31 | Apparence par défaut : pièce gris bleuté satiné, arêtes gris foncé, sans isoparamétriques, lumière principale en haut à gauche | Couleurs d'origine d'OpenCascade peu lisibles (laiton, traits jaunes, faces de même teinte) |
| 2026-10-31 | Sélection : clic = sélectionner, Ctrl + clic = ajouter (comme SolidWorks) ; surbrillance remplie bleu clair au survol, bleu franc à la sélection | IHM-04 |
| 2026-10-31 | Mesure rapide affichée en permanence dans la barre d'état ; Évaluer > Mesurer ouvre un panneau détaillé à gauche ; nombres à la française (virgule) | IHM-12 |
| 2026-10-31 | Éclairage : phare d'origine incliné + ambiante 0,55 (pièce gris bleuté 0,60/0,65/0,73) | Vue de face sans saturation, faces de teintes différentes en isométrique |
| 2026-10-31 | Toute modification d'un document passe par une commande annulable (`cao/document/historique.py`), sans limite ; nouveau paquet `cao.document` sans Qt | Exigence « réversible » §2.1 ; base de l'enregistrement (1.6) |
| 2026-10-31 | Boutons Annuler / Rétablir à côté de Fichier ; Ctrl+Z, Ctrl+Y (et Ctrl+Maj+Z) | Comme SolidWorks et la plupart des logiciels |
| 2026-10-31 | Format natif : archive ZIP contenant document.json (+ géométrie B-Rep au lot 3) ; écriture via fichier temporaire ; numéro de version de format | DOC-07 lisible et documenté ; §8.4 aucune corruption ; compatibilité ascendante |
| 2026-10-31 | Sauvegarde automatique dans un dossier de récupération séparé (jamais dans le fichier de l'utilisateur), copies effacées à la fermeture normale | DOC-03 et §8.4 sans écraser le travail sans accord |
| 2026-10-31 | Dépôt GitHub public ; e-mail des enregistrements remplacé par l'adresse anonyme GitHub avant le premier envoi | Logiciel libre GPL (Actions gratuites) ; ne pas publier l'e-mail personnel de Simon |
| 2026-10-31 | Esquisse : les courbes désignent des points par identifiant (P1, L1, C1, A1) ; points partagés entre courbes reliées ; arcs toujours en sens trigonométrique ; arc centre-extrémités : la fin ne donne que l'angle (comme SolidWorks) | Base du solveur (2.2) et de la détection des contours (2.8) |
| 2026-10-31 | Solveur : la tangence sans extrémité commune et le point sur un arc passent par des éléments d'aide invisibles ; chaque relation est vérifiée avant l'appel au solveur (python-solvespace ignore en silence une entité refusée) | Limites constatées de python-solvespace |
| 2026-10-31 | Extensions de fichiers .caop (pièce), .caoa (assemblage), .caom (mise en plan) | Choix par défaut appliqué (Simon a validé l'étape sans demander de changement) |
| 2026-10-31 | Outils pas encore programmés : cliquables, affichent « Pas encore disponible » dans la barre d'état (au lieu d'être grisés) | Interface plus vivante ; à remplacer outil par outil |

## Lots et avancement

| Lot | Contenu | Exigences | État |
| --- | --- | --- | --- |
| 0. Prototypes | Cube affiché, extrusion + STEP, solveur, vue HLR | — | Terminé (2026-10-31) |
| 1. Socle | Fenêtre, navigation 3D, arbre, fichiers | IHM, ARB, DOC (P1) | Fait sauf 1.7 (intégration continue, reportée) |
| 2. Esquisse | Entités, relations, solveur, cotation | ESQ, GEO, OUT, REL, COT (P1) | En cours |
| 3. Fonctions | Extrusions, révolutions, congés, répétitions | VOL, HAB, REP, REF, PRO (P1) | À faire |
| 4. Assemblage | Insertion, contraintes, déplacement | ASM, CTR, ANA (P1) | À faire |
| 5. Mise en plan | Vues, coupes, cotation, nomenclature, PDF, STEP, STL | MEP, VUE, ANN, NOM, SOR, ECH (P1) | À faire |
| 6. Version 1.0 | Exigences P2, installeurs, aide, tests utilisateurs | P2 | À faire |

## Points ouverts restants

- Compte GitHub : Simon le crée (étape 1.7)

## Journal des séances

- **2026-10-31 :** lecture des documents, réécriture de CLAUDE.md, création de PLAN.md et du dossier docs/. Installation de Miniforge, création de l'environnement `cao`, vérification : import OCC + PySide6 + solvespace OK, boîte 100×50×20 créée. Dépôt Git initialisé, premier commit. Décision : documents d'origine laissés à la racine. Prototype 0.2 écrit et lancé automatiquement sans erreur ; navigation façon SolidWorks (molette = rotation, Ctrl + molette = panoramique). 0.2 validée par Simon et commitée. Prototype 0.3 : plaque 100×50×20 percée Ø10, export STEP, volumes conformes ; ouvert dans FreeCAD par Simon, commité. Prototype 0.4 : rectangle contraint résolu exactement par python-solvespace (0 degré de liberté ; 1 sans la cote de hauteur), commité. Prototype 0.5 : vue de face HLR, arêtes vues en continu fort et cachées en interrompu fin ; note : HLR classe aussi en cachées les arêtes arrière superposées aux arêtes vues, à masquer sous le trait vu en mise en plan. 0.5 validée visuellement par Simon, commitée. Phase 0 terminée. Décisions : GPL 3, python-solvespace, français seul. Étape 1.1 : squelette du logiciel, pyproject.toml, README, LICENSE, docs/architecture.md, tests d'architecture (vérifiés : une faute volontaire est bien détectée). Étape 1.2 : fenêtre principale (ruban 6 onglets aux outils grisés, arbre/propriétés, barre d'affichage, vue 3D, barre d'état, menu Fichier) ; textes regroupés dans `ihm/textes.py` ; tests d'interface sans écran. Simon juge l'interface « années 2000 » : refonte (thème, icônes SVG, ruban groupé et adaptatif, barre d'état en pastilles), vérifiée sur captures à plusieurs largeurs. Simon rappelle que pièce, assemblage et mise en plan sont 3 modules séparés : fenêtre « Nouveau document », une fenêtre par document avec interface propre, gestionnaire des documents ouverts. Correction de l'erreur OpenGL à la fermeture. Barre du haut amincie à la demande de Simon (166 → 74 px). Étape 1.2 validée et commitée. Étape 1.3 : `noyau/affichage.py` (orientations, cube de vue, zoom au point, rendus, apparence, éclairage), branchement des commandes dans la fenêtre ; essai réel : zoom au point écart 0 px, clic sur cube OK, captures des 4 vues et 4 rendus vérifiées ; découverte et correction du décalage des clics dû à l'agrandissement Windows 125 %. Pendant l'essai de Simon : erreur au clic sur la pièce (conversion forcée en « propriétaire de cube ») ; corrigé en testant la nature de l'objet cliqué, vérifié par clic simulé (pièce sélectionnée, cube toujours actif). Étape 1.3 validée par Simon et commitée. Étape 1.4 : `noyau/mesure.py` (10 tests sur boîte 100×50×20 : arête de 100 mm exacte), sélection/filtre/surbrillance/normale dans `noyau/affichage.py`, panneau Mesure, pastille de mesure ; corrections trouvées à l'essai réel : surbrillance limitée au contour (remplie maintenant), face vue de face saturée en blanc (éclairage réglé). Étape 1.4 validée et commitée. Étape 1.5 : annuler/rétablir ; Ctrl+Y inopérant (déclaré deux fois) corrigé ; validée et commitée. Étape 1.6 : enregistrement/ouverture/sauvegarde automatique/récupération ; les tests se bloquaient sur la question « Enregistrer avant de fermer ? » → réponses automatiques dans conftest.py. Simon : « il n'ouvre pas la pièce » → parcours d'ouverture vérifié correct par simulation ; cause probable : relance avec le Python du système (3.15, « No module named cao ») ; ajout de `lancer_cao.bat` à double-cliquer. Étape 1.6 validée et commitée ; 1.7 préparée puis reportée par Simon (pas de compte GitHub). Lot 2 commencé : 2.1 modèle d'esquisse ; 2.2 relations et solveur (essais préalables : normale 3D pour arcs et cercles, numérotation des conflits, point sur arc non géré).
