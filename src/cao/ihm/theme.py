"""Thème visuel : couleurs, police, feuille de style.

Toutes les couleurs sont déclarées une seule fois ici (dictionnaire COULEURS),
pour pouvoir ajouter plus tard un thème sombre (IHM-08) sans toucher au reste.
"""

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

COULEURS: dict[str, str] = {
    "fond": "#eef1f5",  # fond général de la fenêtre
    "surface": "#ffffff",  # panneaux, ruban
    "surface_douce": "#f7f9fc",
    "bordure": "#dde3ea",
    "texte": "#1c2430",
    "texte_doux": "#5f6b7a",
    "accent": "#2563eb",  # bleu principal
    "accent_fonce": "#1f4e99",
    "accent_pale": "#e3ecfd",
    "survol": "#eef3fd",
}

POLICES = '"Segoe UI Variable Text", "Segoe UI", "Ubuntu", "Noto Sans", "Cantarell", sans-serif'


def taille_police_pour_ecran(hauteur_ecran_px: int) -> int:
    """Taille de police de base (points) selon la hauteur utile de l'écran.

    Petit écran (portable 1366 x 768) -> 9 pt ; écran courant -> 10 pt ;
    grand écran -> 11 pt. Windows ajoute ensuite sa propre mise à l'échelle.
    """
    if hauteur_ecran_px < 800:
        return 9
    if hauteur_ecran_px < 1300:
        return 10
    return 11


def feuille_de_style(taille_police: int) -> str:
    c = COULEURS
    petite = max(taille_police - 1, 8)
    return f"""
* {{ font-family: {POLICES}; font-size: {taille_police}pt; color: {c["texte"]}; }}
QMainWindow {{ background: {c["fond"]}; }}

/* Barre de menus + recherche */
QMenuBar {{ background: {c["surface"]}; padding: 4px 8px; border: none; }}
QMenuBar::item {{ padding: 6px 12px; border-radius: 6px; background: transparent; }}
QMenuBar::item:selected {{ background: {c["survol"]}; }}
QMenu {{ background: {c["surface"]}; border: 1px solid {c["bordure"]}; border-radius: 8px;
        padding: 6px; }}
QMenu::item {{ padding: 7px 28px 7px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: {c["accent_pale"]}; color: {c["accent_fonce"]}; }}
QMenu::item:disabled {{ color: #a7b0bd; }}
QMenu::separator {{ height: 1px; background: {c["bordure"]}; margin: 5px 8px; }}
QLineEdit#recherche {{ background: {c["surface_douce"]}; border: 1px solid {c["bordure"]};
        border-radius: 8px; padding: 5px 10px; }}
QLineEdit#recherche:disabled {{ color: {c["texte_doux"]}; }}

/* Ruban */
QTabWidget#ruban {{ background: {c["surface"]}; }}
QTabWidget#ruban::pane {{ border: none; border-bottom: 1px solid {c["bordure"]};
        background: {c["surface"]}; }}
QTabWidget#ruban > QTabBar {{ background: {c["surface"]}; }}
QTabWidget#ruban > QTabBar::tab {{ background: transparent; border: none; padding: 6px 14px;
        margin: 0 2px; color: {c["texte_doux"]}; border-bottom: 2px solid transparent; }}
QTabWidget#ruban > QTabBar::tab:hover {{ color: {c["texte"]}; }}
QTabWidget#ruban > QTabBar::tab:selected {{ color: {c["accent"]}; font-weight: 600;
        border-bottom: 2px solid {c["accent"]}; }}
QWidget#coin_recherche {{ background: {c["surface"]}; }}
QWidget#page_ruban {{ background: {c["surface"]}; }}
QFrame#separateur_groupe {{ background: {c["bordure"]}; border: none; margin: 5px 6px; }}
QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 6px;
        padding: 3px 6px; }}
QToolButton#bouton_fichier {{ background: {c["accent"]}; color: #ffffff; font-weight: 600;
        border: none; border-radius: 6px; padding: 4px 16px; margin: 3px 10px 3px 6px; }}
QToolButton#bouton_fichier:hover {{ background: {c["accent_fonce"]}; }}
QToolButton#bouton_fichier::menu-indicator {{ image: none; width: 0; }}
QToolButton:hover {{ background: {c["survol"]}; border-color: {c["accent_pale"]}; }}
QToolButton:pressed, QToolButton:checked {{ background: {c["accent_pale"]}; }}

/* Panneau gauche */
QWidget#panneau_gauche {{ background: {c["surface"]}; border-right: 1px solid {c["bordure"]}; }}
QLabel#titre_panneau {{ color: {c["texte_doux"]}; font-size: {petite}pt; font-weight: 600;
        letter-spacing: 1px; padding: 12px 14px 6px 14px; }}
QTreeWidget#arbre {{ border: none; background: transparent; padding: 0 6px; outline: 0; }}
QTreeWidget#arbre::item {{ padding: 5px 4px; border-radius: 6px; }}
QTreeWidget#arbre::item:hover {{ background: {c["survol"]}; }}
QTreeWidget#arbre::item:selected {{ background: {c["accent_pale"]}; color: {c["accent_fonce"]}; }}
QSplitter::handle {{ background: {c["fond"]}; width: 4px; }}
QSplitter::handle:hover {{ background: {c["accent_pale"]}; }}

/* Barre d'affichage au-dessus de la vue 3D */
QToolBar#barre_affichage {{ background: {c["surface"]}; border: none;
        border-bottom: 1px solid {c["bordure"]}; padding: 3px 8px; spacing: 2px; }}

/* Barre d'état */
QStatusBar {{ background: {c["surface"]}; border-top: 1px solid {c["bordure"]}; }}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {c["texte_doux"]}; font-size: {petite}pt; }}
QLabel#pastille {{ background: {c["surface_douce"]}; border: 1px solid {c["bordure"]};
        border-radius: 9px; padding: 1px 10px; margin: 3px 3px; }}
/* Fenêtre « Nouveau document » */
QDialog#dialogue_nouveau {{ background: {c["fond"]}; }}
QLabel#consigne_nouveau {{ font-size: {taille_police + 4}pt; font-weight: 600; }}
QPushButton#carte_document {{ background: {c["surface"]}; border: 1px solid {c["bordure"]};
        border-radius: 14px; text-align: center; }}
QPushButton#carte_document:hover {{ border: 2px solid {c["accent"]}; background: {c["survol"]}; }}
QPushButton#carte_document:focus {{ border: 2px solid {c["accent"]}; }}
QLabel#carte_titre {{ font-size: {taille_police + 3}pt; font-weight: 600;
        background: transparent; }}
QLabel#carte_description {{ color: {c["texte_doux"]}; background: transparent; }}
QPushButton#bouton_secondaire {{ background: {c["surface"]}; border: 1px solid {c["bordure"]};
        border-radius: 8px; padding: 7px 18px; }}
QPushButton#bouton_secondaire:hover {{ background: {c["survol"]}; }}

QLabel#pastille_mesure {{ background: {c["accent_pale"]}; color: {c["accent_fonce"]};
        border-radius: 9px; padding: 1px 10px; margin: 3px 3px; font-weight: 600; }}
QLabel#consigne_panneau {{ color: {c["texte_doux"]}; }}
QLabel#resultats_mesure {{ font-size: {taille_police + 1}pt; line-height: 150%; }}
QToolButton#bouton_filtre {{ padding: 3px 4px; }}

QWidget#coin_fichier {{ background: {c["surface"]}; }}
QToolButton#bouton_historique {{ padding: 3px; margin: 3px 0; }}

QToolButton#bouton_quitter_esquisse {{ background: {c["accent"]}; color: #ffffff;
        font-weight: 600; border-radius: 6px; padding: 3px 10px; margin-right: 12px; }}
QToolButton#bouton_quitter_esquisse:hover {{ background: {c["accent_fonce"]}; }}

QToolTip {{ background: {c["texte"]}; color: #ffffff; border: none; padding: 6px 8px;
        border-radius: 6px; }}
"""


def appliquer_theme(application: QApplication, hauteur_ecran_px: int) -> int:
    """Applique le style moderne à toute l'application ; renvoie la taille de police.

    Appliqué une seule fois : les fenêtres suivantes réutilisent le même thème.
    """
    deja = application.property("taille_police_cao")
    if isinstance(deja, int):
        return deja
    application.setStyle("Fusion")  # même rendu sous Windows et Linux
    palette = application.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COULEURS["fond"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(COULEURS["surface"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COULEURS["accent"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(COULEURS["texte"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COULEURS["texte"]))
    application.setPalette(palette)
    taille = taille_police_pour_ecran(hauteur_ecran_px)
    police = QFont(application.font())
    police.setPointSize(taille)
    application.setFont(police)
    application.setStyleSheet(feuille_de_style(taille))
    application.setProperty("taille_police_cao", taille)
    return taille
