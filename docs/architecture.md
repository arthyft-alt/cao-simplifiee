# Architecture du logiciel

> Mis à jour à chaque lot. Dernière mise à jour : 2026-10-31 (étape 1.2).

## Principe

Trois couches, de haut en bas :

1. **Interface (`ihm`)** : fenêtres, ruban, arbre, vue 3D, panneaux. Seule couche qui utilise Qt (PySide6). Elle ne fait aucun calcul géométrique : elle transmet les demandes de l'utilisateur à la couche métier et affiche le résultat.
2. **Métier (`esquisse`, `piece`, `assemblage`, `plan`, `fichiers`)** : la logique de la CAO. Testable sans ouvrir de fenêtre.
3. **Noyau (`noyau`)** : enveloppe autour d'OpenCascade (pythonocc-core). C'est le seul endroit qui appelle `OCC.Core`, pour isoler cette bibliothèque énorme et peu documentée.

Le solveur d'esquisse (python-solvespace) est appelé uniquement par `esquisse`.

## Documents

Comme dans SolidWorks, **pièce**, **assemblage** et **mise en plan** sont trois types de documents distincts (DOC-01). Chacun s'ouvre dans **sa propre fenêtre**, avec son propre ruban, son arbre et sa zone graphique (vue 3D pour pièce et assemblage, feuille 2D pour la mise en plan). Ils communiquent par références de fichiers (DOC-04, étape 1.6 puis lot 4) : un assemblage utilise des pièces, une mise en plan représente une pièce ou un assemblage. Le `GestionnaireDocuments` connaît toutes les fenêtres ouvertes et portera cette communication.

## Vue 3D

- Convention d'axes de SolidWorks : **Y vers le haut**. Plan de face = XY, dessus = XZ, droite = YZ.
- `ihm/vue3d.py` reçoit les événements Qt et les convertit en **pixels réels** (`devicePixelRatioF`) avant de les passer à OpenCascade : indispensable sur un écran agrandi par Windows.
- `noyau/affichage.py` fait tous les calculs de vue ; il reçoit la `V3d_View` et l'`AIS_InteractiveContext`.
- Les commandes du ruban et de la barre d'affichage ont un identifiant (`Outil.commande`) ; la fenêtre les relie aux méthodes de la vue (`FenetreDocument.brancher_commandes_vue`). Une commande sans identifiant affiche « Pas encore disponible ».
- Sélection (IHM-04) : clic = sélectionner, Ctrl + clic = ajouter/retirer ; filtre Tout / Faces / Arêtes / Sommets ; la vue émet `selection_changee(list)`, la fenêtre affiche la mesure rapide dans la barre d'état et le panneau Mesure.
- Hors du noyau, une forme OpenCascade se désigne par le type `cao.noyau.mesure.Forme` (pas d'import d'OCC.Core).
- Éclairage : on règle les deux lumières d'origine (phare + ambiante) ; ne jamais vider `Viewer.ActiveLights()` (pythonocc renvoie la vraie liste).
- Pour afficher une forme, utiliser `noyau.affichage.afficher_forme` (et non `DisplayShape` de pythonocc, qui impose sa propre matière).

## Modifications du document : toujours par une commande

Toute modification d'un document passe par une `Commande` (méthodes `executer` et `annuler`) exécutée par `document.historique.executer(...)`. Elle devient ainsi annulable (Ctrl+Z) et rétablissable (Ctrl+Y), sans limite dans la séance. Plusieurs commandes formant une seule action utilisateur se regroupent avec `with historique.groupe("libellé"):`. Si une commande échoue, la pile reste inchangée. La fenêtre est prévenue par `historique.abonner(...)` et met à jour titre (étoile), arbre et boutons.

## Fenêtres de dialogue et tests

Les fenêtres de dialogue (choix d'un fichier, « Enregistrer avant de fermer ? », messages d'erreur, récupération) sont isolées dans des méthodes dédiées (`choisir_chemin_enregistrement`, `demander_avant_fermeture`, `afficher_erreur`, `choisir_fichier_a_ouvrir`, `demander_recuperation`). `tests/conftest.py` les remplace par des réponses automatiques : **aucun test ne doit ouvrir une fenêtre qui attend une réponse** (sinon les tests se bloquent).

## Paquets

| Paquet | Rôle | Peut importer |
| --- | --- | --- |
| `cao.noyau` | Formes, booléens, congés, projection HLR, propriétés de masse | OCC.Core |
| `cao.esquisse` | Entités 2D, relations, cotes, degré de contrainte | python_solvespace, noyau |
| `cao.piece` | Fonctions volumiques, arbre de construction, reconstruction | noyau, esquisse |
| `cao.assemblage` | Composants, contraintes d'assemblage, interférences | noyau, piece |
| `cao.plan` | Vues, cotation, cartouche, nomenclature | noyau, piece, assemblage |
| `cao.document` | Document commun (nom, type, historique annuler / rétablir) | fichiers |
| `cao.fichiers` | Format natif, récupération, STEP, STL, DXF | noyau, document et paquets métier |
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
├── noyau/
│   └── affichage.py  vue 3D : orientations (Y vers le haut), cube de vue, zoom au point,
│                     modes de rendu, apparence et éclairage, sélection et filtre (sans Qt)
│   └── mesure.py     mesure rapide (IHM-12) : longueur, aire, rayon, distance, angle
├── esquisse/
│   ├── geometrie.py  calculs plans : cercle par 3 points, arc tangent, rectangles (sans dépendance)
│   └── esquisse.py   modèle d'esquisse : points P1…, lignes L1…, cercles C1…, arcs A1… ;
│                     les courbes désignent des points (partagés = contour relié) ;
│                     relations R1… (REL-01 à 05) vérifiées à l'ajout
│   └── solveur.py    pont vers python-solvespace : résout, recopie, degrés de liberté,
│                     relations en conflit (voir ses particularités en tête du fichier)
├── document/
│   ├── historique.py  annuler / rétablir : Commande, CommandeGroupee, PileAnnulation (sans Qt)
│   └── document.py    Document (type, nom, historique) ; CommandeRenommer
├── fichiers/
│   ├── format_natif.py   enregistrer / ouvrir (ZIP + document.json) — voir docs/format_fichier.md
│   ├── recuperation.py   sauvegarde automatique et récupération après plantage
│   └── types_documents.py  les 3 types de documents (DOC-01), numérotation Pièce1, Assemblage1…
└── ihm/
    ├── textes.py    TOUS les textes affichés (IHM-09) ; onglets du ruban PAR type de document
    ├── gestionnaire.py  une fenêtre par document ; ouvre « Nouveau document » ; fera communiquer les documents
    ├── nouveau_document.py  fenêtre de choix Pièce / Assemblage / Mise en plan
    ├── fenetre.py   fenêtre d'un document : ruban, arbre, vue 3D ou feuille, barre d'état selon le type
    ├── feuille.py   zone graphique de la mise en plan (feuille de dessin 2D)
    ├── theme.py     couleurs, police, feuille de style (taille de police selon l'écran)
    ├── icones.py    icônes vectorielles SVG dessinées pour le projet
    ├── ruban.py     ruban à onglets groupés, s'adapte à la largeur (grand / moyen / compact)
    ├── arbre.py     arbre de construction / panneau de propriétés (même emplacement)
    ├── vue3d.py     visualiseur OpenCascade, navigation à la molette
    └── panneaux/
        └── mesure.py  panneau « Mesure » (remplace l'arbre pendant la mesure)
tests/               même découpage que src/cao
├── conftest.py      tests d'interface sans écran (Qt « offscreen »)
└── ihm/             la fenêtre est testée avec avec_vue3d=False (pas de carte graphique en test)
└── pieces_reference/  pièces de recette R1 à R8
prototypes/          scripts jetables de la phase 0 (hors logiciel)
```
