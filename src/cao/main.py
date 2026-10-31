"""Point d'entrée du logiciel.

Lancement : python -m cao            -> fenêtre « Nouveau document », puis le document choisi
            python -m cao fichier.caop -> ouvre ce fichier
            python -m cao --version  -> affiche le nom et la version
"""

import sys
from pathlib import Path

from cao import NOM_APPLICATION, __version__


def texte_version() -> str:
    """Texte de version, par exemple « CAO simplifiée 0.1.0 »."""
    return f"{NOM_APPLICATION} {__version__}"


def main() -> None:
    if "--version" in sys.argv:
        print(texte_version())
        return

    # Imports ici : afficher la version ne doit pas charger Qt ni OpenCascade.
    from PySide6.QtWidgets import QApplication

    from cao.ihm.gestionnaire import GestionnaireDocuments

    application = QApplication(sys.argv)
    application.setApplicationName(NOM_APPLICATION)
    application.setApplicationVersion(__version__)
    gestionnaire = GestionnaireDocuments()
    ouverts = gestionnaire.proposer_recuperation()  # après une fermeture inattendue
    # Fichiers passés au lancement (double-clic sur un fichier, une fois installé).
    for argument in sys.argv[1:]:
        if not argument.startswith("-") and gestionnaire.ouvrir_fichier(Path(argument)):
            ouverts += 1
    if ouverts == 0 and gestionnaire.demander_nouveau() is None:
        return  # « Annuler » au lancement : on quitte
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
