"""Tous les textes affichés par l'interface, regroupés ici (exigence IHM-09).

Aucun texte visible ne doit être écrit en dur ailleurs dans `ihm` : on le
déclare ici puis on l'importe. Une traduction future consistera à fournir
une autre version de ce fichier.

Chaque type de document (pièce, assemblage, mise en plan) a son propre ruban,
comme dans SolidWorks : voir ONGLETS_PAR_TYPE.
"""

from typing import Final, NamedTuple

from cao.fichiers.types_documents import TypeDocument


class Outil(NamedTuple):
    nom: str  # texte du bouton
    info: str  # phrase d'explication de l'info-bulle (AID-01)
    icone: str  # nom de l'icône dans icones.DESSINS
    commande: str = ""  # identifiant de la commande programmée ("" : pas encore disponible)
    raccourci: str = ""  # raccourci clavier, ex. "Ctrl+1"


class Groupe(NamedTuple):
    nom: str  # légende affichée sous le groupe de boutons
    outils: list[Outil]


class Onglet(NamedTuple):
    nom: str
    groupes: list[Groupe]


APPLICATION: Final = "CAO simplifiée"

# --- Fenêtre « Nouveau document » ---
NOUVEAU_TITRE: Final = "Nouveau document"
NOUVEAU_CONSIGNE: Final = "Que voulez-vous créer ?"
NOUVEAU_ANNULER: Final = "Annuler"

# --- Menu Fichier (barre de titre) ---
MENU_FICHIER: Final = "&Fichier"
ACTION_NOUVEAU: Final = "&Nouveau…"
ACTION_OUVRIR: Final = "&Ouvrir…"
ACTION_ENREGISTRER: Final = "&Enregistrer"
ACTION_ENREGISTRER_SOUS: Final = "Enregistrer &sous…"
ACTION_FERMER: Final = "&Fermer"
ACTION_QUITTER: Final = "&Quitter"
RECHERCHE_COMMANDE: Final = "Rechercher…  Ctrl+K"

# --- Enregistrer / ouvrir (étape 1.6) ---
NOUVEAU_OUVRIR: Final = "Ouvrir un document…"
TITRE_OUVRIR: Final = "Ouvrir un document"
TITRE_ENREGISTRER_SOUS: Final = "Enregistrer sous"
FILTRE_TOUS: Final = "Documents CAO"
TITRE_ERREUR_OUVERTURE: Final = "Impossible d'ouvrir le document"
TITRE_ERREUR_ENREGISTREMENT: Final = "Impossible d'enregistrer le document"
TITRE_FERMETURE: Final = "Document modifié"
BOUTON_ENREGISTRER: Final = "Enregistrer"
BOUTON_NE_PAS_ENREGISTRER: Final = "Ne pas enregistrer"
BOUTON_ANNULER: Final = "Annuler"
TITRE_RECUPERATION: Final = "Récupération de documents"
BOUTON_RECUPERER: Final = "Récupérer"
BOUTON_IGNORER: Final = "Ignorer (supprimer les copies)"


def message_enregistre(nom_fichier: str) -> str:
    return f"Enregistré : {nom_fichier}"


def question_fermeture(nom: str) -> str:
    return f"« {nom} » a été modifié.\nEnregistrer les modifications avant de fermer ?"


def question_recuperation(noms: list[str]) -> str:
    liste = "\n".join(f"  • {nom}" for nom in noms)
    return (
        "Le logiciel s'est fermé de façon inattendue. Des copies automatiques "
        f"de ces documents ont été trouvées :\n{liste}\n\nVoulez-vous les récupérer ?"
    )


# --- Annuler / rétablir (Ctrl+Z / Ctrl+Y) ---
ANNULER: Final = "Annuler"
RETABLIR: Final = "Rétablir"
RIEN_A_ANNULER: Final = "Rien à annuler"
RIEN_A_RETABLIR: Final = "Rien à rétablir"


def info_annuler(libelle: str) -> str:
    return f"{ANNULER} : {libelle}" if libelle else RIEN_A_ANNULER


def info_retablir(libelle: str) -> str:
    return f"{RETABLIR} : {libelle}" if libelle else RIEN_A_RETABLIR


RENOMMER_ASTUCE: Final = "Double-cliquez sur le nom (ou F2) pour renommer le document."

# --- Message des outils pas encore programmés ---
BIENTOT: Final = "Pas encore disponible : arrive dans une prochaine étape."


def message_bientot(nom_outil: str) -> str:
    return f"« {nom_outil} » — {BIENTOT}"


def titre_fenetre(nom_document: str, libelle_type: str) -> str:
    """« Pièce1 (Pièce) — CAO simplifiée » ; [*] affiche une étoile si le document est modifié."""
    return f"{nom_document}[*] ({libelle_type}) — {APPLICATION}"


# --- Ruban : onglets réutilisables ---
_ESQUISSE = Onglet(
    "Esquisse",
    [
        Groupe(
            "Esquisse",
            [Outil("Esquisse", "Créer une esquisse sur un plan ou une face plane.", "esquisse")],
        ),
        Groupe(
            "Tracer",
            [
                Outil("Ligne", "Tracer une ligne point par point.", "ligne"),
                Outil("Rectangle", "Tracer un rectangle.", "rectangle"),
                Outil("Cercle", "Tracer un cercle par centre et rayon.", "cercle"),
                Outil("Arc", "Tracer un arc de cercle.", "arc"),
            ],
        ),
        Groupe(
            "Contraindre",
            [
                Outil(
                    "Cote",
                    "Cotation intelligente : le type de cote dépend de la sélection.",
                    "cote",
                ),
                Outil("Relation", "Ajouter une relation géométrique.", "relation"),
            ],
        ),
        Groupe(
            "Modifier",
            [Outil("Ajuster", "Couper une entité à l'intersection la plus proche.", "ajuster")],
        ),
    ],
)

_FONCTIONS = Onglet(
    "Fonctions",
    [
        Groupe(
            "Matière",
            [
                Outil(
                    "Bossage extrudé", "Ajouter de la matière en extrudant une esquisse.", "bossage"
                ),
                Outil(
                    "Enlèvement extrudé",
                    "Enlever de la matière en extrudant une esquisse.",
                    "enlevement",
                ),
                Outil(
                    "Révolution",
                    "Ajouter de la matière en faisant tourner une esquisse.",
                    "revolution",
                ),
            ],
        ),
        Groupe(
            "Habillage",
            [
                Outil("Congé", "Arrondir des arêtes.", "conge"),
                Outil("Chanfrein", "Chanfreiner des arêtes.", "chanfrein"),
            ],
        ),
        Groupe(
            "Répéter",
            [
                Outil("Symétrie", "Symétriser des fonctions par rapport à un plan.", "symetrie"),
                Outil("Répétition", "Répéter des fonctions en ligne ou en cercle.", "repetition"),
            ],
        ),
        Groupe("Référence", [Outil("Plan", "Créer un plan de référence.", "plan")]),
    ],
)

_ASSEMBLAGE = Onglet(
    "Assemblage",
    [
        Groupe(
            "Composants",
            [Outil("Insérer", "Insérer une pièce ou un sous-assemblage.", "inserer")],
        ),
        Groupe(
            "Positionner",
            [
                Outil(
                    "Contrainte",
                    "Positionner deux composants l'un par rapport à l'autre.",
                    "contrainte",
                ),
                Outil("Déplacer", "Déplacer un composant à la souris.", "deplacer"),
            ],
        ),
    ],
)

_DISPOSITION_VUES = Onglet(
    "Disposition des vues",
    [
        Groupe(
            "Vues",
            [
                Outil("Vues standard", "Placer la vue de face et les vues projetées.", "vues"),
                Outil("Isométrique", "Ajouter une vue isométrique.", "vue_iso"),
                Outil("Coupe", "Créer une vue en coupe.", "coupe"),
            ],
        ),
    ],
)

_ANNOTATION = Onglet(
    "Annotation",
    [
        Groupe(
            "Coter",
            [Outil("Cote", "Cotation intelligente dans la mise en plan.", "cote")],
        ),
        Groupe(
            "Annoter",
            [
                Outil("Note", "Ajouter un texte ou un repère avec flèche.", "note"),
                Outil("Nomenclature", "Insérer la nomenclature de l'assemblage.", "nomenclature"),
            ],
        ),
    ],
)


def _evaluer(*supplementaires: Outil) -> Onglet:
    outils = [
        Outil(
            "Mesurer",
            "Mesurer une distance, un angle, un rayon ou une aire entre entités sélectionnées.",
            "mesurer",
            "mesurer",
        )
    ]
    outils += supplementaires
    outils.append(Outil("Propriétés de masse", "Volume, masse, centre de gravité.", "masse"))
    return Onglet("Évaluer", [Groupe("Analyser", outils)])


_AFFICHAGE = Onglet(
    "Affichage",
    [
        Groupe(
            "Rendu",
            [
                Outil(
                    "Ombré avec arêtes",
                    "Faces ombrées et arêtes en noir.",
                    "ombre",
                    "rendu_ombre_aretes",
                ),
                Outil("Ombré", "Faces ombrées, sans les arêtes.", "ombre_simple", "rendu_ombre"),
                Outil("Filaire", "Toutes les arêtes, sans faces.", "filaire", "rendu_filaire"),
                Outil(
                    "Lignes cachées",
                    "Seulement les arêtes visibles, comme sur un dessin technique.",
                    "cachees",
                    "rendu_lignes_cachees",
                ),
            ],
        ),
    ],
)

ONGLETS_PAR_TYPE: Final[dict[TypeDocument, list[Onglet]]] = {
    TypeDocument.PIECE: [_ESQUISSE, _FONCTIONS, _evaluer(), _AFFICHAGE],
    TypeDocument.ASSEMBLAGE: [
        _ASSEMBLAGE,
        _evaluer(Outil("Interférences", "Détecter les pièces qui se chevauchent.", "interference")),
        _AFFICHAGE,
    ],
    TypeDocument.MISE_EN_PLAN: [_DISPOSITION_VUES, _ANNOTATION, _ESQUISSE],
}

# --- Barre d'affichage (haut de la zone 3D, pièce et assemblage) ---
BARRE_AFFICHAGE: Final[list[Outil]] = [
    Outil("Isométrique", "Vue isométrique.", "vue_iso", "vue_isometrique", "Ctrl+7"),
    Outil("Face", "Vue de face (plan XY).", "vue_face", "vue_face", "Ctrl+1"),
    Outil("Dessus", "Vue de dessus (plan XZ).", "vue_dessus", "vue_dessus", "Ctrl+5"),
    Outil("Droite", "Vue de droite (plan YZ).", "vue_droite", "vue_droite", "Ctrl+4"),
    Outil(
        "Normale à",
        "Regarder la face plane sélectionnée de face.",
        "vue_normale",
        "vue_normale",
        "Ctrl+8",
    ),
    Outil("Ajuster", "Ajuster la vue au modèle.", "ajuster_vue", "ajuster", "F"),
]

# --- Filtre de sélection (IHM-04), menu de la barre d'affichage ---
FILTRE_TITRE: Final = "Filtre de sélection"
FILTRES: Final[list[Outil]] = [
    Outil("Tout", "Faces, arêtes et sommets.", "sel_tout", "filtre_tout"),
    Outil("Faces", "Seulement les faces.", "sel_face", "filtre_faces"),
    Outil("Arêtes", "Seulement les arêtes.", "sel_arete", "filtre_aretes"),
    Outil("Sommets", "Seulement les sommets.", "sel_sommet", "filtre_sommets"),
]
VUE_NORMALE_IMPOSSIBLE: Final = "« Normale à » : sélectionnez d'abord une face plane."

# --- Mesure (IHM-12) ---
MESURE_TITRE: Final = "Mesure"
MESURE_CONSIGNE: Final = (
    "Cliquez sur une ou deux entités : face, arête ou sommet. "
    "Ctrl + clic pour ajouter une deuxième entité."
)
MESURE_RIEN: Final = "Rien à mesurer pour cette sélection."
MESURE_FERMER: Final = "Fermer"

# --- Arbre de construction ---
ARBRE_TITRE: Final[dict[TypeDocument, str]] = {
    TypeDocument.PIECE: "Arbre de construction",
    TypeDocument.ASSEMBLAGE: "Arbre de l'assemblage",
    TypeDocument.MISE_EN_PLAN: "Feuilles et vues",
}
ARBRE_ORIGINE: Final = "Origine"
ARBRE_PLANS: Final[list[str]] = ["Plan de face", "Plan de dessus", "Plan de droite"]
ARBRE_CONTRAINTES: Final = "Contraintes"
ARBRE_FEUILLE: Final = "Feuille1"
PANNEAU_PROPRIETES: Final = "Propriétés"
PANNEAU_VIDE: Final = "Aucune fonction en cours d'édition."

# --- Barre d'état ---
ETAT_UNITES: Final = "mm"
ETAT_COORDONNEES: Final = "x —   y —   z —"
ETAT_PAR_TYPE: Final[dict[TypeDocument, list[str]]] = {
    TypeDocument.PIECE: [ETAT_COORDONNEES, "Pas d'esquisse en cours", ETAT_UNITES],
    TypeDocument.ASSEMBLAGE: [ETAT_COORDONNEES, "Aucun composant", ETAT_UNITES],
    TypeDocument.MISE_EN_PLAN: ["Feuille A4 paysage", "Échelle 1:1", ETAT_UNITES],
}
ASTUCE_PAR_TYPE: Final[dict[TypeDocument, str]] = {
    TypeDocument.PIECE: (
        "Astuce : clic molette pour tourner, Ctrl + clic molette pour déplacer, "
        "clic sur le cube pour changer de vue."
    ),
    TypeDocument.ASSEMBLAGE: "Astuce : insérez d'abord une pièce, elle sera fixée à l'origine.",
    TypeDocument.MISE_EN_PLAN: "Astuce : commencez par « Vues standard » pour placer les vues.",
}
