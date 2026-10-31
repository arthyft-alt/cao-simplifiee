"""Point d'entrée du logiciel.

Lancement : python -m cao   (ou la commande « cao » une fois le projet installé)

Pour l'instant (étape 1.1), il affiche seulement le nom et la version.
La fenêtre principale arrive à l'étape 1.2.
"""

from cao import NOM_APPLICATION, __version__


def texte_version() -> str:
    """Texte affiché au lancement, par exemple « CAO simplifiée 0.1.0 »."""
    return f"{NOM_APPLICATION} {__version__}"


def main() -> None:
    print(texte_version())


if __name__ == "__main__":
    main()
