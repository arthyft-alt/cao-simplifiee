"""Icônes vectorielles du logiciel, dessinées pour ce projet (licence du projet).

Chaque icône est un petit dessin SVG sur une grille de 24 x 24. Deux mots-clés
sont remplacés au moment du rendu :
    {trait}   couleur des traits
    {fond}    couleur des surfaces (teinte claire)
Les icônes restent nettes à toutes les tailles, donc sur tous les écrans.
"""

from functools import cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_DEBUT = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{trait}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
)
_FIN = "</svg>"
GRIS_DESACTIVE = "#a7b0bd"

# Cube isométrique réutilisé par plusieurs icônes.
_CUBE = (
    '<path d="M12 3 20 7.5v9L12 21l-8-4.5v-9z" fill="{fond}"/>'
    '<path d="M4 7.5 12 12l8-4.5M12 12v9"/>'
)

DESSINS: dict[str, str] = {
    # --- Esquisse ---
    "esquisse": '<path d="M3 17 9 21l12-6-6-4z" fill="{fond}"/><path d="m14 3 3 3-7 7H7v-3z"/>',
    "ligne": '<path d="M5 19 19 5"/><circle cx="5" cy="19" r="1.8" fill="{fond}"/>'
    '<circle cx="19" cy="5" r="1.8" fill="{fond}"/>',
    "rectangle": '<rect x="4" y="6" width="16" height="12" rx="1" fill="{fond}"/>',
    "cercle": '<circle cx="12" cy="12" r="8" fill="{fond}"/><path d="M12 12h8"/>'
    '<circle cx="12" cy="12" r="1" fill="{trait}"/>',
    "arc": '<path d="M4 18a8 8 0 0 1 16 0"/><circle cx="4" cy="18" r="1.6" fill="{fond}"/>'
    '<circle cx="20" cy="18" r="1.6" fill="{fond}"/>',
    "cote": '<path d="M4 7v10M20 7v10M6 12h12"/><path d="m8 10-2 2 2 2M16 10l2 2-2 2"/>',
    "relation": '<path d="M5 19h14M8 19V5"/><path d="M8 15h4v4"/>',
    "ajuster": '<circle cx="6" cy="7" r="2.5"/><circle cx="6" cy="17" r="2.5"/>'
    '<path d="M8 8.5 20 16M8 15.5 20 8"/>',
    # --- Fonctions ---
    "bossage": '<path d="M4 15 12 19l8-4-8-4z" fill="{fond}"/><path d="M12 3v10"/>'
    '<path d="m9 6 3-3 3 3"/>',
    "enlevement": '<path d="M12 3 20 7.5v9L12 21l-8-4.5v-9z" fill="{fond}"/>'
    '<ellipse cx="12" cy="9" rx="3.5" ry="2" fill="#ffffff"/><path d="M12 12v5"/>'
    '<path d="m10 15 2 2 2-2"/>',
    "revolution": '<path d="M12 2v20" stroke-dasharray="2 2.5"/>'
    '<ellipse cx="12" cy="12" rx="8" ry="3.5" fill="{fond}"/><path d="m18 6 2 2.5-3 .5"/>'
    '<path d="M20 8.5A8 3.5 0 0 0 12 5"/>',
    "conge": '<path d="M4 20V10a6 6 0 0 1 6-6h10v16z" fill="{fond}"/>',
    "chanfrein": '<path d="M4 20V9l5-5h11v16z" fill="{fond}"/>',
    "symetrie": '<path d="M12 3v18" stroke-dasharray="2 2.5"/>'
    '<path d="M9 7 4 17h5z" fill="{fond}"/><path d="m15 7 5 10h-5z"/>',
    "repetition": '<rect x="3.5" y="3.5" width="6" height="6" rx="1" fill="{fond}"/>'
    '<rect x="14.5" y="3.5" width="6" height="6" rx="1"/>'
    '<rect x="3.5" y="14.5" width="6" height="6" rx="1"/>'
    '<rect x="14.5" y="14.5" width="6" height="6" rx="1"/>',
    "plan": '<path d="M2 16 8 6h14l-6 10z" fill="{fond}"/>',
    # --- Assemblage ---
    "inserer": _CUBE + '<path d="M19 15v6M16 18h6"/>',
    "contrainte": '<rect x="3" y="4" width="8" height="8" rx="1.5" fill="{fond}"/>'
    '<rect x="13" y="12" width="8" height="8" rx="1.5" fill="{fond}"/>'
    '<path d="M11 8h4v4"/>',
    "deplacer": '<path d="M12 3v18M3 12h18"/><path d="m9 6 3-3 3 3M9 18l3 3 3-3'
    'M6 9l-3 3 3 3M18 9l3 3-3 3"/>',
    # --- Mise en plan ---
    "vues": '<rect x="3" y="3" width="18" height="18" rx="1.5"/>'
    '<rect x="6" y="6" width="6" height="5" fill="{fond}"/>'
    '<rect x="6" y="13" width="6" height="5" fill="{fond}"/>'
    '<rect x="14" y="6" width="4" height="5" fill="{fond}"/>',
    "coupe": '<rect x="5" y="5" width="14" height="14" rx="1" fill="{fond}"/>'
    '<path d="M3 12h18" stroke-dasharray="4 2 1 2"/><path d="M8 8l4 4M12 8l4 4"/>',
    "nomenclature": '<rect x="3" y="4" width="18" height="16" rx="1.5"/>'
    '<path d="M3 9h18M3 14h18M8 4v16"/>',
    # --- Évaluer ---
    "mesurer": '<path d="m3 16 13-13 5 5-13 13z" fill="{fond}"/>'
    '<path d="m7 12 2 2M10 9l2 2M13 6l2 2"/>',
    "masse": '<path d="M6 9h12l2 11H4z" fill="{fond}"/><circle cx="12" cy="6" r="2.5"/>',
    # --- Affichage ---
    "ombre": _CUBE,
    "ombre_simple": '<path d="M12 3 20 7.5v9L12 21l-8-4.5v-9z" fill="{fond}"/>',
    "filaire": _CUBE.replace('fill="{fond}"', "")
    + '<path d="M4 16.5 12 12l8 4.5" stroke-dasharray="1.5 2"/>',
    "cachees": '<path d="M12 3 20 7.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/>'
    '<path d="M4 16.5 12 12" stroke-dasharray="1.5 2" opacity=".5"/>',
    # --- Barre d'affichage ---
    "vue_iso": _CUBE,
    "vue_face": '<rect x="5" y="5" width="14" height="14" rx="1" fill="{fond}"/>',
    "vue_dessus": '<path d="M3 15 9 7h12l-6 8z" fill="{fond}"/><path d="M12 15v5"/>',
    "vue_droite": '<path d="M8 4 16 8v12l-8-4z" fill="{fond}"/>',
    "ajuster_vue": '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>'
    '<rect x="8" y="8" width="8" height="8" rx="1" fill="{fond}"/>',
    # --- Arbre ---
    "piece": _CUBE,
    "origine": '<path d="M5 19V5M5 19h14"/><path d="m3 7 2-2 2 2M17 17l2 2-2 2"/>'
    '<circle cx="5" cy="19" r="1.5" fill="{trait}"/>',
    "recherche": '<circle cx="11" cy="11" r="6"/><path d="m20 20-4.5-4.5"/>',
    "note": '<path d="M4 4h16v12H10l-4 4v-4H4z" fill="{fond}"/><path d="M8 8h8M8 12h5"/>',
    "interference": '<rect x="3" y="3" width="11" height="11" rx="1.5"/>'
    '<rect x="10" y="10" width="11" height="11" rx="1.5"/>'
    '<rect x="10" y="10" width="4" height="4" fill="{trait}"/>',
    "feuille": '<rect x="3" y="5" width="18" height="14" rx="1" fill="{fond}"/>'
    '<path d="M13 19v-4h8"/>',
    "dossier": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8'
    'a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" fill="{fond}"/>',
}


def svg(nom: str, trait: str, fond: str) -> str:
    """Texte SVG complet de l'icône, avec ses couleurs."""
    corps = DESSINS[nom].replace("{trait}", trait).replace("{fond}", fond)
    return _DEBUT.replace("{trait}", trait) + corps + _FIN


def _pixmap(nom: str, trait: str, fond: str, taille: int) -> QPixmap:
    rendu = QSvgRenderer(QByteArray(svg(nom, trait, fond).encode("utf-8")))
    image = QPixmap(taille, taille)
    image.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(image)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    rendu.render(peintre, QRectF(0, 0, taille, taille))
    peintre.end()
    return image


@cache
def icone(nom: str, trait: str = "#1f4e99", fond: str = "#dbe7fb") -> QIcon:
    """Icône prête pour un bouton ; version pâle automatique quand il est désactivé."""
    resultat = QIcon()
    for taille in (16, 20, 24, 32, 40, 48, 64):
        resultat.addPixmap(_pixmap(nom, trait, fond, taille), QIcon.Mode.Normal)
        resultat.addPixmap(_pixmap(nom, GRIS_DESACTIVE, "#f1f3f6", taille), QIcon.Mode.Disabled)
    return resultat
