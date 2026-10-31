"""Point d'entrée du logiciel.

Lancement : python -m cao            -> fenêtre « Nouveau document », puis le document choisi
            python -m cao --version  -> affiche le nom et la version
"""

import sys

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
    if gestionnaire.demander_nouveau() is None:
        return  # « Annuler » au lancement : on quitte
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
