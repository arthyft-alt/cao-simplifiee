# Cahier des charges — Logiciel de CAO simplifié

Oct 31, 2026 · @Simon

## 1. Présentation du projet

Le logiciel à réaliser est un modeleur 3D paramétrique simplifié, inspiré de SolidWorks, couvrant trois modules : **Pièce**, **Assemblage** et **Mise en plan**. Il vise la prise en main en moins d'une heure par un débutant, au prix d'un périmètre volontairement réduit.

### 1.1 Contexte et besoin

Les logiciels de CAO professionnels sont puissants mais lourds : licences coûteuses, installation exigeante, interface dense. Le besoin est un outil léger qui reprend leur logique de travail (esquisse contrainte → fonction volumique → assemblage → plan) pour concevoir des pièces simples et apprendre la démarche de conception.

### 1.2 Objectifs

- Modéliser des pièces mécaniques simples par fonctions paramétriques modifiables à tout moment.
- Assembler plusieurs pièces avec des contraintes de position et vérifier les mouvements.
- Produire une mise en plan normalisée (ISO) imprimable et exportable en PDF.
- Offrir une interface moderne, épurée et guidée, utilisable sans formation préalable.

### 1.3 Public cible

| Profil | Usage principal | Niveau attendu |
| --- | --- | --- |
| Élève / étudiant (BTS, bac pro, IUT) | Apprendre la démarche de conception, réaliser des pièces de TP | Débutant |
| Formateur | Préparer des modèles, des plans et des exercices | Intermédiaire |
| Technicien de maintenance | Redessiner une pièce de rechange simple, faire un plan coté | Intermédiaire |
| Amateur / maker | Concevoir des pièces pour impression 3D | Débutant à intermédiaire |

### 1.4 Périmètre

**Inclus :** esquisse 2D contrainte, fonctions volumiques de base, assemblage par contraintes, mise en plan avec cotation et nomenclature, import/export de formats d'échange courants.

**Exclus (hors version 1) :** surfaces complexes, tôlerie, soudure, simulation par éléments finis, rendu photoréaliste, travail collaboratif en temps réel, gestion de données techniques (PDM).

### 1.5 Conventions du document

Chaque exigence porte un identifiant (ex. `ESQ-04`) et une priorité :

- **P1** — indispensable à la première version utilisable (MVP).
- **P2** — attendue dans la version 1.0.
- **P3** — souhaitable, version ultérieure.

## 2. Interface utilisateur

L'interface reprend la disposition familière des modeleurs 3D (ruban en haut, arbre à gauche, vue 3D au centre) mais n'affiche à chaque instant que les outils utiles au contexte. L'objectif est zéro menu imbriqué au-delà de deux niveaux.

### 2.1 Principes ergonomiques

- **Contextuel** : le ruban change selon le mode (esquisse, pièce, assemblage, plan) et grise les outils inapplicables.
- **Direct** : sélectionner une face ou une arête propose les actions pertinentes dans une mini-barre flottante.
- **Guidé** : chaque fonction ouvre un panneau de propriétés avec aperçu en temps réel, validation ✓ et annulation ✗.
- **Réversible** : annuler / rétablir illimité dans la session (Ctrl+Z / Ctrl+Y).
- **Lisible** : thème clair et sombre, icônes vectorielles avec libellé au survol, contraste conforme WCAG AA.

### 2.2 Zones de l'écran

| Zone | Position | Contenu |
| --- | --- | --- |
| Barre de titre | Haut | Nom du document, état d'enregistrement, menu fichier, recherche de commande |
| Ruban à onglets | Sous la barre de titre | Onglets Esquisse, Fonctions, Assemblage, Mise en plan, Évaluer, Affichage |
| Arbre de construction | Gauche | Historique des fonctions, plans de référence, origine, composants |
| Panneau de propriétés | Gauche, en remplacement de l'arbre | Paramètres de la fonction en cours d'édition |
| Zone graphique | Centre | Vue 3D ou feuille de plan, triade d'orientation, cube de vue |
| Barre d'affichage | Haut de la zone graphique | Vues standard, mode de rendu, coupe, zoom ajusté |
| Barre d'état | Bas | Unités, état de l'esquisse (sous-contrainte / totalement contrainte), coordonnées du curseur, astuces |

### 2.3 Exigences

| ID | Exigence | Priorité |
| --- | --- | --- |
| IHM-01 | Navigation 3D à la souris : rotation (clic molette), panoramique (Ctrl + clic molette), zoom (molette) centré sur le curseur | P1 |
| IHM-02 | Cube de vue cliquable (faces, arêtes, coins) et vues standard : face, dessus, droite, isométrique, normale à la sélection | P1 |
| IHM-03 | Modes de rendu : ombré avec arêtes, ombré, filaire, lignes cachées supprimées | P1 |
| IHM-04 | Surbrillance au survol des faces, arêtes et sommets avant sélection ; filtre de sélection | P1 |
| IHM-05 | Mini-barre contextuelle au clic sur une entité (esquisser, extruder, coter, masquer…) | P2 |
| IHM-06 | Recherche de commande par mot-clé (Ctrl+K) | P2 |
| IHM-07 | Raccourcis clavier personnalisables et menu radial au clic droit maintenu | P3 |
| IHM-08 | Thèmes clair et sombre, taille d'interface réglable (100 / 125 / 150 %) | P2 |
| IHM-09 | Interface en français, textes externalisés pour traduction | P1 |
| IHM-10 | Vue en coupe dynamique selon un plan, déplaçable | P2 |
| IHM-11 | Mode tutoriel : bulles d'aide pas à pas pour la première pièce | P3 |
| IHM-12 | Mesure rapide : distance, angle, rayon, aire entre entités sélectionnées | P1 |

## 3. Module Pièce — Esquisse 2D

L'esquisse est le point de départ de toute fonction volumique : un profil 2D tracé sur un plan ou une face plane, piloté par des relations géométriques et des cotes. Le solveur de contraintes doit recalculer l'esquisse en moins de 100 ms pour 200 entités.

### 3.1 Création et édition d'esquisse

| ID | Exigence | Priorité |
| --- | --- | --- |
| ESQ-01 | Créer une esquisse sur un plan de référence (face, dessus, droite) ou sur une face plane du modèle ; la vue s'oriente automatiquement normale au plan | P1 |
| ESQ-02 | Quitter l'esquisse par un bouton de validation visible en coin de zone graphique | P1 |
| ESQ-03 | Rééditer une esquisse existante depuis l'arbre ; le modèle se reconstruit à la sortie | P1 |
| ESQ-04 | Inférence automatique pendant le tracé : alignement horizontal / vertical, point milieu, coïncidence, tangence, avec repères pointillés | P1 |
| ESQ-05 | Saisie numérique directe des longueurs et angles pendant le tracé (champ flottant près du curseur) | P2 |
| ESQ-06 | Grille et accrochage activables, pas réglable | P2 |
| ESQ-07 | Code couleur de l'état : bleu = sous-contraint, noir = totalement contraint, rouge = sur-contraint ou en conflit | P1 |
| ESQ-08 | Lignes de construction (pointillés) non prises en compte dans le profil | P1 |
| ESQ-09 | Détection des contours fermés et sélection de la région à utiliser par la fonction | P1 |

### 3.2 Entités géométriques

| ID | Entité | Modes de tracé | Priorité |
| --- | --- | --- | --- |
| GEO-01 | Ligne | Point–point, chaînée | P1 |
| GEO-02 | Rectangle | Deux coins, centré, trois points incliné | P1 |
| GEO-03 | Cercle | Centre–rayon, trois points | P1 |
| GEO-04 | Arc | Centre–extrémités, trois points, tangent | P1 |
| GEO-05 | Polygone régulier | Inscrit / circonscrit, nombre de côtés | P2 |
| GEO-06 | Rainure (oblong) | Droite, centrée | P2 |
| GEO-07 | Ellipse | Centre–axes | P3 |
| GEO-08 | Spline | Points de passage | P3 |
| GEO-09 | Point et axe de construction | Libre | P1 |
| GEO-10 | Texte d'esquisse | Police système, pour gravure | P3 |

### 3.3 Outils d'esquisse

| ID | Outil | Priorité |
| --- | --- | --- |
| OUT-01 | Ajuster (couper à l'intersection la plus proche, par glissement) | P1 |
| OUT-02 | Prolonger | P2 |
| OUT-03 | Congé et chanfrein d'esquisse | P1 |
| OUT-04 | Décaler les entités (offset) | P2 |
| OUT-05 | Symétrie d'entités par rapport à une ligne | P1 |
| OUT-06 | Répétition linéaire et circulaire d'entités | P2 |
| OUT-07 | Convertir les entités (projeter une arête du modèle dans l'esquisse) | P2 |
| OUT-08 | Déplacer, copier, faire pivoter, mettre à l'échelle | P2 |

### 3.4 Relations géométriques

Les relations sont ajoutées automatiquement par inférence ou manuellement après sélection. Elles s'affichent sous forme de pictogrammes près des entités, masquables, et se suppriment par sélection + Suppr.

| ID | Relation | Priorité |
| --- | --- | --- |
| REL-01 | Horizontale, verticale | P1 |
| REL-02 | Coïncidente, point milieu, fixe | P1 |
| REL-03 | Parallèle, perpendiculaire, colinéaire | P1 |
| REL-04 | Tangente, concentrique | P1 |
| REL-05 | Égale (longueurs ou rayons) | P1 |
| REL-06 | Symétrique par rapport à une ligne | P2 |
| REL-07 | Diagnostic des conflits : liste des relations en cause, proposition de suppression | P2 |

### 3.5 Cotation intelligente

Un seul outil « Cote » déduit le type de cote de la sélection, comme la cotation intelligente de SolidWorks.

| Sélection | Cote créée |
| --- | --- |
| Une ligne | Longueur (horizontale, verticale ou alignée selon la position du curseur) |
| Deux points ou un point et une ligne | Distance |
| Deux lignes non parallèles | Angle |
| Deux lignes parallèles | Distance entre elles |
| Un cercle | Diamètre (rayon au choix) |
| Un arc | Rayon |
| Un cercle et une ligne ou deux cercles | Distance centre à centre ou tangente au choix |

| ID | Exigence | Priorité |
| --- | --- | --- |
| COT-01 | À la pose, un champ de saisie apparaît ; la géométrie se met à jour à la validation | P1 |
| COT-02 | Double-clic sur une cote pour la modifier, dans l'esquisse comme sur le modèle 3D | P1 |
| COT-03 | Saisie d'expressions : opérations (`50/2+3`) et références à d'autres cotes ou variables (`D1*2`) | P2 |
| COT-04 | Tableau des variables globales de la pièce (nom, valeur, unité) | P3 |
| COT-05 | Cote pilotée (de référence, entre parenthèses) quand l'esquisse est déjà contrainte | P2 |
| COT-06 | Unités mm, cm, m, pouce ; précision d'affichage réglable | P1 |

## 4. Module Pièce — Fonctions volumiques

Chaque fonction crée ou modifie le solide à partir d'une esquisse ou d'arêtes et faces existantes, et s'inscrit dans l'arbre de construction. Toute fonction reste éditable : changer un paramètre reconstruit le modèle en aval.

### 4.1 Comportement commun

- Aperçu translucide en temps réel pendant le réglage des paramètres.
- Poignées graphiques (flèches) pour tirer une profondeur ou un angle à la souris.
- Option **Fusionner le résultat** (par défaut) ou création d'un corps séparé.
- Message clair en cas d'échec de reconstruction, avec la fonction fautive signalée en rouge dans l'arbre.

### 4.2 Fonctions d'ajout et d'enlèvement de matière

| ID | Fonction | Paramètres principaux | Priorité |
| --- | --- | --- | --- |
| VOL-01 | Bossage extrudé | Profondeur borgne, jusqu'à la face, à travers tout, plan milieu ; deux directions ; dépouille | P1 |
| VOL-02 | Enlèvement de matière extrudé | Mêmes conditions de fin que VOL-01 ; inverser le côté | P1 |
| VOL-03 | Bossage avec révolution | Axe (ligne de construction), angle 0–360°, deux directions | P1 |
| VOL-04 | Enlèvement de matière avec révolution | Idem VOL-03 | P1 |
| VOL-05 | Bossage / enlèvement balayé | Profil + trajectoire (deux esquisses) | P3 |
| VOL-06 | Bossage / enlèvement lissé | Deux profils ou plus sur plans parallèles | P3 |
| VOL-07 | Coque | Épaisseur, faces à retirer | P2 |
| VOL-08 | Nervure | Esquisse ouverte, épaisseur, sens | P3 |

### 4.3 Fonctions d'habillage

| ID | Fonction | Paramètres principaux | Priorité |
| --- | --- | --- | --- |
| HAB-01 | Congé | Rayon constant, sélection d'arêtes ou de faces, propagation tangente | P1 |
| HAB-02 | Chanfrein | Distance–distance ou distance–angle | P1 |
| HAB-03 | Assistance pour le perçage | Trou simple, lamé, fraisé, taraudé ; tailles normalisées ISO M3 à M20 ; placement par points d'esquisse | P2 |
| HAB-04 | Dépouille | Plan neutre, faces, angle | P3 |
| HAB-05 | Filetage cosmétique | Représentation simplifiée pour la mise en plan | P3 |

### 4.4 Fonctions de répétition et de symétrie

| ID | Fonction | Paramètres principaux | Priorité |
| --- | --- | --- | --- |
| REP-01 | Symétrie | Plan ou face plane ; fonctions ou corps à symétriser | P1 |
| REP-02 | Répétition linéaire | Une ou deux directions, nombre d'occurrences, pas ou longueur totale | P1 |
| REP-03 | Répétition circulaire | Axe, nombre, angle total ou pas angulaire, espacement égal | P1 |
| REP-04 | Occurrences à ignorer dans une répétition | Clic sur l'occurrence dans l'aperçu | P2 |

### 4.5 Géométrie de référence

| ID | Élément | Définition | Priorité |
| --- | --- | --- | --- |
| REF-01 | Plan | Décalé d'un plan ou d'une face, par trois points, incliné autour d'une arête, plan médian | P1 |
| REF-02 | Axe | Par deux points, arête, axe d'une face cylindrique, intersection de deux plans | P1 |
| REF-03 | Point | Sommet, centre d'arc, projection | P2 |
| REF-04 | Système de coordonnées | Origine + orientation | P3 |

### 4.6 Propriétés de la pièce

| ID | Exigence | Priorité |
| --- | --- | --- |
| PRO-01 | Bibliothèque de matériaux (acier, aluminium, laiton, ABS, PLA, bois…) avec masse volumique et couleur | P1 |
| PRO-02 | Propriétés de masse : volume, masse, aire, centre de gravité, moments d'inertie | P2 |
| PRO-03 | Couleur et transparence par pièce, par fonction ou par face | P2 |
| PRO-04 | Propriétés personnalisées (désignation, référence, auteur) reprises dans le cartouche et la nomenclature | P1 |

## 5. Module Assemblage

L'assemblage positionne des pièces (ou sous-assemblages) les unes par rapport aux autres par des contraintes, en référençant les fichiers pièces : modifier une pièce met à jour tous les assemblages qui l'utilisent. Cible : 50 composants et 20 000 faces affichés à 30 images/s sur un ordinateur de bureau courant.

### 5.1 Gestion des composants

| ID | Exigence | Priorité |
| --- | --- | --- |
| ASM-01 | Insérer un composant depuis un fichier ou par glisser-déposer ; le premier composant est fixé à l'origine | P1 |
| ASM-02 | Déplacer et faire pivoter librement un composant non contraint (glisser, triade de manipulation) | P1 |
| ASM-03 | Fixer / libérer un composant | P1 |
| ASM-04 | Masquer, afficher, rendre transparent un composant | P1 |
| ASM-05 | Ouvrir la pièce d'origine depuis l'assemblage ; mise à jour au retour | P1 |
| ASM-06 | Sous-assemblages (assemblage inséré dans un assemblage) | P2 |
| ASM-07 | Répétition linéaire / circulaire de composants, ou calquée sur une répétition de la pièce (ex. vis sur tous les trous) | P2 |
| ASM-08 | Bibliothèque de composants standards : vis CHC et H, écrous, rondelles, goupilles, roulements simplifiés (ISO, tailles M3 à M20) | P3 |
| ASM-09 | Vue éclatée avec étapes, animable | P2 |

### 5.2 Contraintes d'assemblage

Comme pour la cotation intelligente, la contrainte la plus probable est proposée d'après les deux entités sélectionnées ; l'utilisateur peut en choisir une autre.

| ID | Contrainte | Entités typiques | Priorité |
| --- | --- | --- | --- |
| CTR-01 | Coïncidente | Face–face, plan–plan, point–point | P1 |
| CTR-02 | Parallèle, perpendiculaire | Faces, arêtes, axes | P1 |
| CTR-03 | Coaxiale (concentrique) | Faces cylindriques, axes | P1 |
| CTR-04 | Distance | Faces ou plans parallèles | P1 |
| CTR-05 | Angle | Faces ou arêtes | P1 |
| CTR-06 | Tangente | Cylindre–plan, sphère–plan | P2 |
| CTR-07 | Symétrique | Deux faces par rapport à un plan | P3 |
| CTR-08 | Limite (distance ou angle entre bornes min/max) | Faces, arêtes | P3 |
| CTR-09 | Engrenage, pignon-crémaillère, came | Contraintes mécaniques de mouvement | P3 |

| ID | Exigence | Priorité |
| --- | --- | --- |
| CTR-10 | Inversion de l'alignement (aligné / anti-aligné) par un bouton | P1 |
| CTR-11 | Dossier « Contraintes » dans l'arbre ; édition, suppression, désactivation temporaire | P1 |
| CTR-12 | Indication des degrés de liberté restants par composant (−, +, (f)) | P2 |
| CTR-13 | Signalement des contraintes en conflit avec explication | P2 |

### 5.3 Analyse de l'assemblage

| ID | Exigence | Priorité |
| --- | --- | --- |
| ANA-01 | Déplacement d'un composant à la souris en respectant les contraintes (simulation cinématique simple) | P1 |
| ANA-02 | Détection d'interférences entre composants : liste, volume, surbrillance rouge | P2 |
| ANA-03 | Détection de collision pendant le déplacement (arrêt au contact) | P3 |
| ANA-04 | Propriétés de masse de l'assemblage | P2 |

## 6. Module Mise en plan

La mise en plan produit le dessin de définition d'une pièce ou le dessin d'ensemble d'un assemblage, associatif au modèle 3D : toute modification du modèle met à jour les vues et les cotes. Les conventions suivent les normes ISO du dessin technique (projection européenne par défaut).

### 6.1 Feuille et cartouche

| ID | Exigence | Priorité |
| --- | --- | --- |
| MEP-01 | Formats A4 portrait / paysage, A3, A2 ; cadre et repères de centrage | P1 |
| MEP-02 | Cartouche normalisé rempli automatiquement depuis les propriétés (titre, référence, matière, échelle, auteur, date, établissement) | P1 |
| MEP-03 | Modèle de cartouche personnalisable (logo, champs) et réutilisable | P2 |
| MEP-04 | Projection européenne (ISO E) ou américaine (ISO A), symbole affiché dans le cartouche | P1 |
| MEP-05 | Plusieurs feuilles par document | P2 |

### 6.2 Vues

| ID | Vue | Description | Priorité |
| --- | --- | --- | --- |
| VUE-01 | Vues standard | Placement guidé : vue de face, puis vues projetées alignées par glissement | P1 |
| VUE-02 | Vue isométrique | Ombrée ou filaire | P1 |
| VUE-03 | Vue en coupe | Ligne de coupe tracée sur une vue, hachures automatiques selon la matière, désignation A-A | P1 |
| VUE-04 | Demi-coupe et coupe brisée | Ligne de coupe à plusieurs segments | P3 |
| VUE-05 | Vue de détail | Cercle sur une vue, agrandissement à l'échelle choisie | P2 |
| VUE-06 | Vue partielle et coupe locale | Contour d'esquisse fermé | P3 |
| VUE-07 | Vue éclatée d'assemblage | Reprise de la vue éclatée du modèle | P2 |

| ID | Exigence | Priorité |
| --- | --- | --- |
| VUE-08 | Échelle normalisée par vue ou globale (1:5, 1:2, 1:1, 2:1, 5:1…) | P1 |
| VUE-09 | Traits conformes : arêtes vues en continu fort, cachées en interrompu fin, axes en mixte fin | P1 |
| VUE-10 | Affichage des arêtes cachées activable par vue | P1 |
| VUE-11 | Axes et traits de centre ajoutés automatiquement sur les cylindres et trous | P2 |

### 6.3 Cotation et annotations

| ID | Exigence | Priorité |
| --- | --- | --- |
| ANN-01 | Import automatique des cotes du modèle dans les vues | P2 |
| ANN-02 | Cotation intelligente dans le plan (mêmes règles que COT) : longueur, diamètre Ø, rayon R, angle | P1 |
| ANN-03 | Cotation en chaîne, en parallèle et à partir d'une référence | P2 |
| ANN-04 | Tolérances dimensionnelles : écarts ±, limites, classes ISO (H7, g6…) | P2 |
| ANN-05 | Note de texte, repère avec flèche | P1 |
| ANN-06 | État de surface (Ra), tolérances géométriques et références (cadre de tolérance ISO 1101) | P3 |
| ANN-07 | Désignation de trous issue de l'assistance pour le perçage (ex. 4 × M6 – 12) | P3 |
| ANN-08 | Alignement automatique des cotes et anti-chevauchement | P2 |

### 6.4 Nomenclature (dessin d'ensemble)

| ID | Exigence | Priorité |
| --- | --- | --- |
| NOM-01 | Nomenclature générée depuis l'assemblage : repère, nombre, désignation, matière, observations | P1 |
| NOM-02 | Repères (bulles) attachés aux composants, numérotés comme la nomenclature | P1 |
| NOM-03 | Mise à jour automatique à l'ajout ou au retrait d'un composant | P1 |
| NOM-04 | Colonnes personnalisables à partir des propriétés | P2 |

### 6.5 Sorties

| ID | Exigence | Priorité |
| --- | --- | --- |
| SOR-01 | Impression avec choix du format et mise à l'échelle exacte | P1 |
| SOR-02 | Export PDF vectoriel | P1 |
| SOR-03 | Export DXF / DWG 2D | P2 |
| SOR-04 | Export image PNG haute résolution | P2 |

## 7. Fonctions transverses

Ces fonctions sont communes aux trois modules et garantissent la cohérence de l'ensemble : historique paramétrique, gestion des fichiers et échanges avec d'autres logiciels.

### 7.1 Arbre de construction

| ID | Exigence | Priorité |
| --- | --- | --- |
| ARB-01 | Liste chronologique des fonctions avec icône, nom modifiable et esquisse enfant repliable | P1 |
| ARB-02 | Surbrillance réciproque : survol dans l'arbre ↔ surbrillance dans la vue 3D | P1 |
| ARB-03 | Barre de reprise : glisser pour revenir à un état antérieur et insérer une fonction | P2 |
| ARB-04 | Supprimer / exclure une fonction ; avertissement listant les fonctions dépendantes | P1 |
| ARB-05 | Réordonner les fonctions par glisser-déposer quand les dépendances le permettent | P3 |
| ARB-06 | Dossiers pour regrouper des fonctions | P3 |

### 7.2 Gestion des documents

| ID | Exigence | Priorité |
| --- | --- | --- |
| DOC-01 | Trois types de documents : pièce, assemblage, mise en plan, chacun avec son extension propre | P1 |
| DOC-02 | Nouveau document à partir d'un modèle (unités, matière, cartouche par défaut) | P2 |
| DOC-03 | Enregistrement, enregistrement sous, sauvegarde automatique toutes les 5 minutes | P1 |
| DOC-04 | Liens de référence pièce ↔ assemblage ↔ plan ; signalement des fichiers manquants avec possibilité de les relocaliser | P1 |
| DOC-05 | Pack and go : export d'un assemblage et de toutes ses pièces dans une archive unique | P2 |
| DOC-06 | Fichiers récents et vignette d'aperçu | P2 |
| DOC-07 | Format natif lisible et documenté (JSON pour l'historique + géométrie B-Rep) | P1 |

### 7.3 Import et export

| ID | Format | Sens | Usage | Priorité |
| --- | --- | --- | --- | --- |
| ECH-01 | STEP (AP214) | Import / export | Échange 3D avec SolidWorks, Fusion 360, FreeCAD… | P1 |
| ECH-02 | STL | Export | Impression 3D, réglage de la finesse du maillage | P1 |
| ECH-03 | 3MF | Export | Impression 3D avec couleurs | P3 |
| ECH-04 | IGES | Import | Fichiers anciens | P3 |
| ECH-05 | DXF | Import dans une esquisse | Reprise d'un profil 2D | P2 |
| ECH-06 | glTF / GLB | Export | Visualisation web, présentation | P3 |

Les pièces importées en STEP sont des solides « morts » (sans historique) sur lesquels on peut ajouter des fonctions.

### 7.4 Aide et apprentissage

| ID | Exigence | Priorité |
| --- | --- | --- |
| AID-01 | Info-bulle sur chaque outil : nom, raccourci, phrase d'explication | P1 |
| AID-02 | Aide intégrée consultable hors ligne, avec une page par fonction | P2 |
| AID-03 | Tutoriels pas à pas fournis : première pièce, première esquisse contrainte, premier assemblage, premier plan | P2 |
| AID-04 | Bibliothèque d'exemples (5 pièces, 1 assemblage, 2 plans) | P2 |

## 8. Exigences techniques et non fonctionnelles

L'application est un logiciel de bureau écrit en Python, fonctionnant sous Linux et Windows, construit sur des briques open source éprouvées (Qt pour l'interface, OpenCascade pour la géométrie) plutôt que sur un noyau géométrique développé de zéro.

### 8.1 Architecture

&#91;embedded content: architecture logicielle · 3 couches, 7 blocs\]

L'interface Qt n'effectue aucun calcul géométrique : elle transmet les fonctions au cœur applicatif, qui délègue au solveur 2D et au noyau OpenCascade via pythonocc-core (opérations booléennes, congés, projection des vues de plan par l'algorithme HLR, lecture-écriture STEP et STL), puis renvoie la forme à afficher dans la vue OpenGL.

### 8.2 Plateforme et compatibilité

| ID | Exigence | Priorité |
| --- | --- | --- |
| TEC-01 | Programme écrit en Python 3.11 ou supérieur, avec un code source unique pour Linux et Windows | P1 |
| TEC-02 | Fonctionne sous Linux : Ubuntu 22.04 et 24.04 LTS, Debian 12, Linux Mint 21 et suivantes, sessions X11 et Wayland | P1 |
| TEC-03 | Fonctionne sous Windows 10 et 11, 64 bits | P1 |
| TEC-04 | Interface graphique PySide6 (Qt 6) ; vue 3D OpenGL par le visualiseur pythonOCC intégré à Qt | P1 |
| TEC-05 | Linux : distribution en AppImage autonome, lançable sans rien installer | P1 |
| TEC-06 | Windows : installeur .exe (PyInstaller + Inno Setup) avec raccourci, associations de fichiers et désinstallation ; version portable en .zip | P1 |
| TEC-07 | Linux : paquet Flatpak publiable sur Flathub | P2 |
| TEC-08 | Environnement de développement reproductible par conda (conda-forge publie pythonocc-core pour Linux et Windows) | P1 |
| TEC-09 | Aucun code propre à un système : chemins via `pathlib`, emplacements des réglages et données via `QStandardPaths`, fins de ligne neutres | P1 |
| TEC-10 | Fichiers natifs identiques sur les deux systèmes : un document créé sous Linux s'ouvre sous Windows et inversement | P1 |
| TEC-11 | Intégration continue compilant et testant chaque version sous Ubuntu et Windows | P2 |
| TEC-12 | Portage macOS non exigé mais non bloqué | P3 |
| TEC-13 | Fonctionne entièrement hors ligne | P1 |
| TEC-14 | Configuration minimale : 8 Go de RAM, carte graphique OpenGL 3.3 (pilotes libres Mesa acceptés sous Linux), écran 1366 × 768 | P1 |

### 8.3 Performances

| ID | Indicateur | Cible |
| --- | --- | --- |
| PERF-01 | Démarrage jusqu'à l'écran d'accueil | < 5 s |
| PERF-02 | Recalcul d'une esquisse de 200 entités | < 100 ms |
| PERF-03 | Reconstruction d'une pièce de 50 fonctions | < 3 s |
| PERF-04 | Fluidité de la vue 3D (50 composants, 20 000 faces) | ≥ 30 images/s |
| PERF-05 | Mise à jour d'une mise en plan de 4 vues après modification | < 5 s |

### 8.4 Fiabilité et données

- Sauvegarde automatique et récupération après fermeture inattendue (DOC-03).
- Aucune donnée envoyée sur Internet : fichiers stockés localement, pas de compte obligatoire.
- Compatibilité ascendante du format natif : un fichier de la version N s'ouvre en version N+1.
- Un échec de fonction ne doit jamais corrompre le document ni bloquer l'interface.

### 8.5 Qualité et maintenabilité

- Code Python annoté (types vérifiés par mypy), formaté par ruff, découpé en paquets : `ihm`, `esquisse`, `piece`, `assemblage`, `plan`, `fichiers`.
- Calculs longs (reconstruction, mise à jour des plans) dans un thread de travail Qt, pour ne jamais figer l'interface.
- Tests automatisés pytest sur le solveur, les fonctions volumiques et les imports/exports, avec une base de pièces de référence.
- Licences compatibles avec la diffusion : pythonocc-core et PySide6 sous LGPL 3 ; python-solvespace sous GPL 3, ce qui impose une diffusion du logiciel sous GPL 3 si ce solveur est retenu.

### 8.6 Points à trancher

- Validation Windows : tester tôt (dès le lot 1) l'affichage OpenGL sur les postes réels de l'établissement, notamment les cartes graphiques Intel intégrées et les sessions bureau à distance, qui sont les cas les plus fragiles.

* Diffusion : usage interne gratuit, logiciel libre, ou produit commercial ? Cela conditionne les licences possibles.
* Solveur d'esquisse : python-solvespace (prêt à l'emploi, GPL 3) ou adaptation du solveur planegcs de FreeCAD (LGPL, plus de travail d'intégration) ?
* Langue : français seul, ou français et anglais dès la version 1.0 ?

## 9. Planning, livrables et recette

Le développement est découpé en six lots livrables séparément ; une pièce simple est modélisable dès la fin du lot 3, et la première version complète (toutes les exigences P1) arrive à la fin du lot 5. Les durées sont indicatives, pour un développeur à temps plein, et seront affinées après le lot 1.

### 9.1 Lots de développement

| Lot | Contenu | Exigences couvertes | Durée indicative | Jalon de fin |
| --- | --- | --- | --- | --- |
| 1. Socle | Interface, vue 3D et navigation, arbre, gestion des fichiers, intégration du noyau | IHM, ARB, DOC (P1) | 4 semaines | Une boîte s'affiche et s'enregistre |
| 2. Esquisse | Entités, outils, relations, solveur, cotation intelligente | ESQ, GEO, OUT, REL, COT (P1) | 6 semaines | Esquisse totalement contrainte |
| 3. Fonctions | Extrusions, révolutions, congés, chanfreins, symétrie, répétitions, plans de référence, matériaux | VOL, HAB, REP, REF, PRO (P1) | 6 semaines | **Pièce MVP** |
| 4. Assemblage | Insertion, contraintes, déplacement contraint | ASM, CTR, ANA (P1) | 5 semaines | Assemblage contraint et mobile |
| 5. Mise en plan | Feuille, cartouche, vues, coupes, cotation, nomenclature, PDF ; import/export STEP et STL | MEP, VUE, ANN, NOM, SOR, ECH (P1) | 6 semaines | **MVP complet (P1)** |
| 6. Version 1.0 | Exigences P2, aide et tutoriels, tests utilisateurs, corrections | Toutes P2 | 8 semaines | **Version 1.0** |

Durée totale indicative : 35 semaines. Les exigences P3 forment le carnet des versions suivantes.

### 9.2 Livrables

- Application Linux au format AppImage (et Flatpak au lot 6) et installeur Windows .exe, construits à partir du même code source.
- Code source commenté, avec instructions de compilation.
- Format de fichier natif documenté.
- Aide intégrée, quatre tutoriels pas à pas et la bibliothèque d'exemples (AID-02 à AID-04).
- Cahier de recette rempli, avec les résultats de chaque scénario.

### 9.3 Critères de recette

Chaque lot est validé par des scénarios d'usage réels, et non par une simple liste de fonctions cochées.

| N° | Scénario | Critère d'acceptation |
| --- | --- | --- |
| R1 | Modéliser une équerre de fixation : extrusion, enlèvement, 2 trous répétés, congés, symétrie | Réalisée par un débutant en moins de 20 min après le tutoriel |
| R2 | Modifier une cote de l'esquisse de base de R1 | Toute la pièce se reconstruit sans erreur |
| R3 | Modéliser un axe épaulé par révolution, avec chanfreins et gorge | Volume calculé conforme à ±0,1 % du calcul théorique |
| R4 | Assembler une bride : 2 pièces et 4 vis contraintes | Aucun degré de liberté parasite ; détection d'interférence correcte |
| R5 | Dessin de définition A4 de R1 : 3 vues, 1 coupe, cotation complète | PDF imprimé à l'échelle 1:1 avec écart < 0,5 mm |
| R6 | Dessin d'ensemble de R4 avec nomenclature et repères | Nomenclature exacte, mise à jour après retrait d'une vis |
| R7 | Export STEP de R1 et R4 | Réouverture sans erreur dans FreeCAD et SolidWorks |
| R8 | Export STL de R1 | Fichier étanche, accepté par un trancheur d'impression 3D |
| R9 | Mesure des performances | Indicateurs PERF-01 à PERF-05 atteints |
| R10 | Test d'utilisabilité avec 5 utilisateurs débutants | Score SUS ≥ 70 ; aucune tâche R1, R4, R5 abandonnée |
