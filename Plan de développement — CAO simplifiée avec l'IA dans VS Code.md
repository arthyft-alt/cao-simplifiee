# Plan de développement — CAO simplifiée avec l'IA dans VS Code

Oct 31, 2026 · @Simon

Ce plan décrit comment développer le logiciel défini dans le cahier des charges en faisant écrire l'essentiel du code par un assistant IA dans Visual Studio Code, en environ 40 semaines. Le principe : de très petites étapes, chacune testée et enregistrée dans Git avant de passer à la suivante.

## 1. Mise en place (semaine 1)

L'éditeur retenu est **Visual Studio Code** (gratuit, Linux et Windows), l'outil standard pour Python ; Visual Studio « classique » est surtout fait pour C# et C++.

### 1.1 Logiciels à installer

| Outil | Rôle | Remarque |
| --- | --- | --- |
| Visual Studio Code | Éditeur et terminal | Même configuration sous Linux et Windows |
| Miniforge (conda) | Environnement Python isolé | Seul moyen simple d'installer pythonocc-core |
| Git + compte GitHub | Historique, retour arrière, sauvegarde | Indispensable avec une IA : chaque étape doit pouvoir être annulée |
| Extension Python + Pylance | Exécution, débogage, autocomplétion | — |
| Extension Ruff | Formatage et détection d'erreurs | — |
| Assistant IA en mode agent | Écrit et modifie le code, lance les tests | GitHub Copilot (mode agent) ou Claude Code (extension VS Code) ; un seul suffit |

### 1.2 Environnement Python

```bash
conda create -n cao python=3.11
conda activate cao
conda install -c conda-forge pythonocc-core pyside6 pytest
pip install python-solvespace ruff mypy
```

Premier test, avant toute autre chose : faire afficher par l'IA un cube OpenCascade dans une fenêtre Qt, sous Linux **et** sous Windows. Si cet affichage échoue, rien d'autre ne sert.

### 1.3 Fichiers d'instructions pour l'IA

L'IA ne se souvient pas d'une session à l'autre : elle relit à chaque fois des fichiers placés à la racine du projet. Ce sont eux qui garantissent la cohérence sur 40 semaines.

| Fichier | Contenu |
| --- | --- |
| `docs/cahier_des_charges.md` | Le cahier des charges complet, avec les identifiants d'exigences |
| `CLAUDE.md` ou `.github/copilot-instructions.md` | Règles permanentes : versions, bibliothèques autorisées, conventions de nommage, structure, « toujours écrire un test », « ne jamais modifier un test pour le faire passer » |
| `docs/architecture.md` | Le rôle de chaque paquet et qui appelle qui ; mis à jour à chaque lot |
| `docs/journal.md` | Ce qui est fait, ce qui reste, les décisions prises ; l'IA le met à jour en fin de séance |

## 2. Méthode de travail avec l'IA

Vous jouez le rôle de chef de projet et de testeur ; l'IA joue celui du développeur. Chaque séance répète la même boucle, d'une à deux heures par exigence.

&#91;embedded content: boucle de travail avec l'IA · 6 étapes\]

Après trois essais ratés, on revient à l'étape 2 : la demande était trop grosse ou mal posée, il faut la découper.

### 2.1 Règles d'or

1. **Une exigence par demande.** « Fais le module esquisse » produit un code inutilisable ; « Fais l'outil Ligne (GEO-01), mode point-point » fonctionne.
2. **Plan avant code.** Demander d'abord « explique comment tu vas faire et quels fichiers tu vas toucher », valider, puis lancer.
3. **Toujours un test.** Une fonction sans test automatique n'est pas terminée. Interdire à l'IA de modifier un test pour le faire passer.
4. **Commit après chaque réussite.** Si l'IA casse tout à l'étape suivante, `git restore .` ramène à l'état sain en une seconde.
5. **Essayer à la main.** Les tests ne voient pas l'interface : ouvrir le logiciel et cliquer après chaque fonction visible.
6. **Nouvelle conversation par tâche.** Une conversation trop longue fait perdre le fil à l'IA ; le journal et les fichiers d'instructions assurent la continuité.
7. **Le moteur avant l'interface.** Pour chaque fonction, faire d'abord la partie calcul (testable sans fenêtre), puis le panneau Qt qui l'appelle.

## 3. Structure du projet

La structure est fixée dès la semaine 1 et décrite dans `docs/architecture.md`, pour que l'IA range chaque nouveau fichier au bon endroit. La séparation clé : les paquets de calcul (`noyau`, `esquisse`, `piece`, `assemblage`, `plan`) n'importent jamais Qt, ce qui permet de les tester sans ouvrir de fenêtre.

```
cao/
├── CLAUDE.md                  # règles permanentes pour l'IA
├── pyproject.toml             # dépendances, ruff, mypy, pytest
├── environment.yml            # environnement conda reproductible
├── docs/
│   ├── cahier_des_charges.md
│   ├── architecture.md
│   └── journal.md
├── src/cao/
│   ├── main.py                # point d'entrée
│   ├── noyau/                 # enveloppe autour de pythonocc-core
│   ├── esquisse/              # entités 2D, relations, solveur
│   ├── piece/                 # fonctions volumiques, arbre, reconstruction
│   ├── assemblage/            # composants, contraintes, interférences
│   ├── plan/                  # vues, cotation, cartouche, nomenclature
│   ├── fichiers/              # format natif, STEP, STL, DXF
│   └── ihm/                   # tout ce qui est Qt
│       ├── fenetre.py
│       ├── vue3d.py
│       ├── ruban.py
│       ├── arbre.py
│       └── panneaux/          # un panneau de propriétés par fonction
├── tests/                     # même découpage que src/cao
│   └── pieces_reference/      # pièces de recette R1 à R8
└── packaging/
    ├── linux/                 # recette AppImage
    └── windows/               # PyInstaller + Inno Setup
```

## 4. Plan étape par étape

Le plan suit les six lots du cahier des charges, précédés de deux semaines de prototypes qui valident les briques techniques avant d'investir dans l'interface. Durée totale indicative : 40 semaines à raison de 10 à 15 heures par semaine ; à temps plein, compter environ la moitié.

| Phase | Semaines | Résultat visible |
| --- | --- | --- |
| 0. Prototypes | 1–2 | Un cube s'affiche sous Linux et Windows ; le solveur résout un rectangle |
| 1. Socle | 3–6 | Fenêtre complète, navigation 3D, enregistrement |
| 2. Esquisse | 7–13 | Esquisse contrainte avec cotation intelligente |
| 3. Fonctions | 14–20 | **Pièce MVP** : l'équerre R1 est modélisable |
| 4. Assemblage | 21–25 | La bride R4 est assemblée et mobile |
| 5. Mise en plan | 26–32 | **MVP complet** : plan A4 de R1 imprimé en PDF |
| 6. Version 1.0 | 33–40 | Installeurs Linux et Windows, aide, tests utilisateurs |

### Phase 0 — Prototypes (semaines 1–2)

Objectif : lever les risques techniques. Ces scripts sont jetables et rangés dans `prototypes/`.

| Étape | À faire | Terminé quand |
| --- | --- | --- |
| 0.1 | Installer l'environnement (section 1), créer le dépôt Git et les fichiers d'instructions | `conda activate cao` puis `python -c "import OCC, PySide6"` sans erreur |
| 0.2 | Afficher une boîte OpenCascade dans une fenêtre PySide6, rotation à la souris | Fonctionne sous Linux et sous Windows |
| 0.3 | Faire une extrusion puis un perçage par opération booléenne, exporter en STEP | Le STEP s'ouvre dans FreeCAD |
| 0.4 | Résoudre un rectangle contraint (horizontal, vertical, 2 cotes) avec python-solvespace | Les coordonnées calculées sont exactes |
| 0.5 | Projeter la boîte en vue de face avec l'algorithme HLR d'OpenCascade, dessiner les traits dans Qt | Arêtes vues et cachées distinguées |

> Exemple de demande : « Dans prototypes/affichage.py, crée une fenêtre PySide6 qui affiche une boîte de 100 × 50 × 20 mm avec le visualiseur Qt de pythonocc-core. Rotation au clic molette. Donne-moi la commande pour lancer le script. »

### Lot 1 — Socle (semaines 3–6)

| Étape | À faire | Exigences | Terminé quand |
| --- | --- | --- | --- |
| 1.1 | Squelette `src/cao`, `pyproject.toml`, ruff, mypy, pytest, premier test | — | `pytest` passe, `ruff check` sans erreur |
| 1.2 | Fenêtre principale : ruban à onglets, arbre à gauche, zone 3D, barre d'état | IHM | Disposition conforme à la section 2.2 du cahier des charges |
| 1.3 | Navigation 3D, cube de vue, vues standard, modes de rendu | IHM-01 à 03 | Essai à la main |
| 1.4 | Sélection avec surbrillance au survol, mesure rapide | IHM-04, IHM-12 | Mesure d'une arête de la boîte exacte |
| 1.5 | Annuler / rétablir (pile de commandes) | — | Test automatique sur 10 actions |
| 1.6 | Format natif : enregistrer et rouvrir un document, sauvegarde automatique | DOC-01, 03, 07 | Un fichier rouvert est identique (test) |
| 1.7 | Intégration continue GitHub Actions sous Ubuntu et Windows | TEC-11 | Badge vert sur le dépôt |

### Lot 2 — Esquisse (semaines 7–13)

C'est le lot le plus délicat : le dialogue entre la souris, le solveur et l'affichage. Faire d'abord tout le modèle et le solveur en pur Python testé, puis l'interface.

| Étape | À faire | Exigences | Terminé quand |
| --- | --- | --- | --- |
| 2.1 | Modèle de données : points, lignes, cercles, arcs, sans affichage | GEO-01 à 04 | Tests de création et de sérialisation |
| 2.2 | Pont vers le solveur : relations horizontale, verticale, coïncidente, parallèle, perpendiculaire, tangente, égale | REL-01 à 05 | Un test par relation |
| 2.3 | Cotes et calcul du degré de contrainte (sous / totalement / sur-contraint) | COT-01, ESQ-07 | Tests sur 5 esquisses types |
| 2.4 | Mode esquisse dans l'interface : plan orienté, tracé des entités, code couleur | ESQ-01, 02, 07 | Essai à la main |
| 2.5 | Inférence automatique pendant le tracé | ESQ-04 | Un rectangle tracé est déjà horizontal / vertical |
| 2.6 | Cotation intelligente : une seule commande, type déduit de la sélection | COT-01, 02, 06 | Les 7 cas du tableau 3.5 du cahier des charges |
| 2.7 | Outils : ajuster, congé d'esquisse, symétrie ; lignes de construction | OUT-01, 03, 05, ESQ-08 | Essai à la main |
| 2.8 | Détection des contours fermés | ESQ-09 | Tests sur profils avec trou intérieur |

### Lot 3 — Fonctions volumiques (semaines 14–20)

| Étape | À faire | Exigences | Terminé quand |
| --- | --- | --- | --- |
| 3.1 | Arbre de construction et reconstruction : chaque fonction est un objet avec ses paramètres et ses références | ARB-01, 04 | Modifier une cote reconstruit la pièce (test) |
| 3.2 | Bossage et enlèvement extrudés, toutes conditions de fin | VOL-01, 02 | Volumes calculés exacts |
| 3.3 | Révolutions | VOL-03, 04 | Pièce R3 : volume à ±0,1 % |
| 3.4 | Panneau de propriétés générique avec aperçu translucide et poignées | — | Essai à la main |
| 3.5 | Plans et axes de référence ; esquisse sur une face | REF-01, 02, ESQ-01 | Esquisse sur la face supérieure d'un bloc |
| 3.6 | Congés et chanfreins | HAB-01, 02 | Tests sur arêtes droites et circulaires |
| 3.7 | Symétrie, répétitions linéaire et circulaire | REP-01 à 03 | 6 trous répétés circulairement |
| 3.8 | Matériaux, propriétés personnalisées | PRO-01, 04 | Masse affichée correcte |
| 3.9 | **Recette R1, R2, R3** | — | Équerre modélisée de bout en bout |

> Le point dur de ce lot est le « nommage topologique » : quand une pièce est reconstruite, la face sur laquelle une esquisse était posée peut changer d'identifiant. Demander à l'IA une solution simple (repérer la face par sa normale et sa position) plutôt qu'une solution générale.

### Lot 4 — Assemblage (semaines 21–25)

| Étape | À faire | Exigences | Terminé quand |
| --- | --- | --- | --- |
| 4.1 | Document assemblage, insertion de pièces par référence, premier composant fixe | ASM-01, 03, 05 | La modification d'une pièce met à jour l'assemblage |
| 4.2 | Déplacement libre avec triade | ASM-02 | Essai à la main |
| 4.3 | Solveur de contraintes 3D : coïncidente, coaxiale, parallèle, distance, angle | CTR-01 à 05 | Un test par contrainte |
| 4.4 | Inversion d'alignement, dossier contraintes dans l'arbre | CTR-10, 11 | Essai à la main |
| 4.5 | Déplacement contraint à la souris | ANA-01 | Une rotation autour d'un axe coaxial |
| 4.6 | **Recette R4** | — | Bride assemblée, aucun degré de liberté parasite |

### Lot 5 — Mise en plan (semaines 26–32)

| Étape | À faire | Exigences | Terminé quand |
| --- | --- | --- | --- |
| 5.1 | Feuille A4/A3, cadre, cartouche rempli depuis les propriétés | MEP-01, 02, 04 | Essai à la main |
| 5.2 | Vues standard projetées (HLR), traits normalisés, échelles | VUE-01, 02, 08 à 10 | 3 vues alignées de R1 |
| 5.3 | Vue en coupe avec hachures | VUE-03 | Coupe A-A de R3 |
| 5.4 | Cotation dans le plan, notes | ANN-02, 05 | Cotes associées aux arêtes |
| 5.5 | Mise à jour associative | — | Modifier R1 met à jour son plan |
| 5.6 | Nomenclature et repères | NOM-01 à 03 | Recette R6 |
| 5.7 | Impression et export PDF ; import/export STEP et STL | SOR-01, 02, ECH-01, 02 | **Recettes R5, R7, R8** |

### Lot 6 — Version 1.0 (semaines 33–40)

| Étape | À faire | Terminé quand |
| --- | --- | --- |
| 6.1 | Exigences P2 par ordre de priorité (coque, perçage, vues de détail, interférences, vue éclatée…) | Chaque exigence avec son test |
| 6.2 | AppImage Linux et installeur Windows ; test sur une machine sans Python | Installation et lancement en moins de 2 min |
| 6.3 | Aide intégrée, 4 tutoriels, bibliothèque d'exemples | Relecture par un collègue |
| 6.4 | Mesures de performances | Recette R9 |
| 6.5 | Tests avec 5 élèves débutants, corrections | Recette R10, score SUS ≥ 70 |

## 5. Pièges de l'IA sur ce projet

Les assistants IA sont très bons pour l'interface Qt et la structure du code, mais moins fiables sur OpenCascade, une bibliothèque C++ énorme et peu documentée en Python. La plupart des blocages viendront de là.

| Piège | Symptôme | Parade |
| --- | --- | --- |
| Fonctions OpenCascade inventées | `AttributeError` ou import introuvable | Toutes les fonctions OCC passent par le paquet `noyau` ; on y ajoute les exemples officiels de pythonocc-core comme référence, et on demande à l'IA de les lire avant d'écrire |
| Versions mélangées | Code écrit pour une ancienne API pythonocc ou PySide2 | Versions exactes notées dans `CLAUDE.md` et `environment.yml` |
| Demande trop large | Des centaines de lignes qui ne marchent pas | Revenir au dernier commit, découper en exigences unitaires |
| Test modifié pour passer | Test vert mais fonction fausse | Règle écrite dans `CLAUDE.md` ; relire chaque modification de `tests/` avant de valider |
| Régression silencieuse | Une fonction qui marchait ne marche plus | Lancer **tous** les tests avant chaque commit, pas seulement le nouveau |
| Interface figée | La fenêtre ne répond plus pendant une reconstruction | Exiger le thread de travail dès la première fonction volumique |
| Code propre à un système | Marche sous Linux, plante sous Windows | Intégration continue sur les deux systèmes dès le lot 1 |
| Conversation trop longue | L'IA oublie les décisions, se contredit | Une conversation par étape ; journal à jour |
| Nommage topologique | Une esquisse « saute » de face après modification | Solution simple et documentée au lot 3 ; ne pas viser la robustesse de SolidWorks |

## 6. Modèles de demandes

Ces modèles se copient tels quels dans l'assistant ; seuls les éléments entre crochets changent.

### 6.1 Contenu de départ de `CLAUDE.md`

```markdown
# Projet CAO simplifiée
Logiciel de CAO paramétrique en Python 3.11, Linux et Windows.
Lire docs/cahier_des_charges.md, docs/architecture.md et docs/journal.md avant toute tâche.

## Technologies (ne pas en ajouter sans demander)
- PySide6 (Qt 6) pour l'interface
- pythonocc-core (OpenCascade) pour la géométrie, uniquement via src/cao/noyau
- python-solvespace pour les esquisses
- pytest, ruff, mypy

## Règles
- Une exigence à la fois ; annoncer le plan et les fichiers touchés avant de coder.
- Tout code de calcul a un test dans tests/ ; ne jamais modifier un test existant pour le faire passer.
- Les paquets noyau, esquisse, piece, assemblage, plan n'importent jamais Qt.
- Chemins avec pathlib, aucun code propre à un système.
- Noms de variables et commentaires en français.
- En fin de tâche : lancer tous les tests, mettre à jour docs/journal.md.
```

### 6.2 Démarrer une exigence

```text
Tâche : [ID] — [intitulé de l'exigence, copié du cahier des charges].
Commence par me présenter ton plan : fichiers créés ou modifiés, tests prévus.
N'écris pas de code avant ma validation.
```

### 6.3 Faire écrire le test d'abord

```text
Plan validé. Écris d'abord les tests dans tests/[paquet]/ pour [ID],
lance-les et montre-moi qu'ils échouent. Puis écris le code jusqu'à ce que
tous les tests du projet passent.
```

### 6.4 Signaler un bug

```text
Bug : [ce que j'ai fait, pas à pas].
Attendu : [résultat attendu]. Obtenu : [résultat obtenu + message d'erreur complet].
Écris d'abord un test qui reproduit le bug, puis corrige.
```

### 6.5 Clore une séance

```text
Lance tous les tests et ruff. Si tout est vert, mets à jour docs/journal.md
(fait, reste à faire, décisions) et propose un message de commit.
```
