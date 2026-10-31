"""Démonstration de l'étape 1.3 : une pièce contenant la plaque percée du prototype 0.3.

Le logiciel ne sait pas encore créer de volume (lot 3) : ce script affiche une
pièce toute faite pour pouvoir essayer la navigation, les vues et les rendus.

Lancement (environnement cao actif) :
    python prototypes/demo_navigation.py
"""

import sys

from extrusion_step import percer, plaque_extrudee
from PySide6.QtWidgets import QApplication

from cao.fichiers.types_documents import TypeDocument
from cao.ihm.gestionnaire import GestionnaireDocuments
from cao.noyau.affichage import VueStandard, afficher_forme


def main() -> None:
    application = QApplication(sys.argv)
    gestionnaire = GestionnaireDocuments()
    fenetre = gestionnaire.ouvrir(TypeDocument.PIECE)
    application.processEvents()  # laisse la vue 3D s'initialiser
    vue = fenetre.zone_graphique
    if not vue.prete:
        vue.InitDriver()
    afficher_forme(vue._display.Context, percer(plaque_extrudee()))
    vue.orienter(VueStandard.ISOMETRIQUE)
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
