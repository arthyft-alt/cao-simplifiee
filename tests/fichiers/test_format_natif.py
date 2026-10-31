"""Tests de l'étape 1.6 : format natif (DOC-01, DOC-07, TEC-10) et récupération (DOC-03).

Critère du plan de développement : un fichier rouvert est identique.
"""

import json
import zipfile
from pathlib import Path

import pytest

from cao.document.document import Document
from cao.fichiers import format_natif, recuperation
from cao.fichiers.format_natif import FichierInvalide
from cao.fichiers.types_documents import TypeDocument


def lire_json(chemin: Path) -> dict[str, object]:
    with zipfile.ZipFile(chemin) as archive:
        return json.loads(archive.read("document.json"))  # type: ignore[no-any-return]


@pytest.mark.parametrize("type_document", list(TypeDocument))
def test_fichier_rouvert_identique(tmp_path: Path, type_document: TypeDocument) -> None:
    document = Document(type_document, "Essai")
    document.contenu = {"exemple": [1, 2.5, "é"]}
    chemin = tmp_path / f"Support{format_natif.extension(type_document)}"
    format_natif.enregistrer(document, chemin)

    rouvert = format_natif.ouvrir(chemin)
    assert rouvert.type_document == type_document
    assert rouvert.nom == "Support"
    assert rouvert.contenu == document.contenu
    assert rouvert.chemin == chemin
    assert not rouvert.modifie

    # Réenregistré, le fichier a exactement le même contenu (hors date d'enregistrement).
    chemin_2 = tmp_path / f"Copie{format_natif.extension(type_document)}"
    format_natif.enregistrer(rouvert, chemin_2)
    premier, second = lire_json(chemin), lire_json(chemin_2)
    for donnees in (premier, second):
        donnees.pop("enregistre_le")
        donnees.pop("nom")
    assert premier == second


def test_enregistrer_donne_son_nom_et_efface_l_etoile(tmp_path: Path) -> None:
    document = Document(TypeDocument.PIECE, "Pièce1")
    document.renommer("Brouillon")
    assert document.modifie
    format_natif.enregistrer(document, tmp_path / "Équerre.caop")
    assert document.nom == "Équerre"
    assert not document.modifie


def test_json_lisible_et_identique_sous_windows_et_linux(tmp_path: Path) -> None:
    chemin = tmp_path / "Pièce.caop"
    format_natif.enregistrer(Document(TypeDocument.PIECE, "Pièce"), chemin)
    with zipfile.ZipFile(chemin) as archive:
        brut = archive.read("document.json")
    assert b"\r\n" not in brut  # fins de ligne neutres
    texte = brut.decode("utf-8")
    assert '"format": "cao-simplifiee"' in texte
    assert '"version_format": 1' in texte
    assert str(tmp_path) not in texte  # aucun chemin absolu dans le fichier


def test_echec_d_ecriture_ne_detruit_pas_l_ancien_fichier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chemin = tmp_path / "Pièce.caop"
    document = Document(TypeDocument.PIECE, "Pièce")
    format_natif.enregistrer(document, chemin)
    avant = chemin.read_bytes()

    def panne(*_args: object, **_kwargs: object) -> None:
        raise OSError("disque plein (simulation)")

    monkeypatch.setattr(format_natif.os, "replace", panne)
    with pytest.raises(OSError):
        format_natif.enregistrer(document, chemin)
    assert chemin.read_bytes() == avant
    assert not list(tmp_path.glob("*.tmp"))  # pas de fichier temporaire oublié


def test_fichier_introuvable(tmp_path: Path) -> None:
    with pytest.raises(FichierInvalide, match="introuvable"):
        format_natif.ouvrir(tmp_path / "absent.caop")


def test_fichier_qui_n_est_pas_un_document(tmp_path: Path) -> None:
    faux = tmp_path / "faux.caop"
    faux.write_text("ceci n'est pas un document", encoding="utf-8")
    with pytest.raises(FichierInvalide, match="n'est pas un document"):
        format_natif.ouvrir(faux)


def test_fichier_d_une_version_plus_recente(tmp_path: Path) -> None:
    chemin = tmp_path / "futur.caop"
    format_natif.ecrire(Document(TypeDocument.PIECE, "Futur"), chemin, {"version_format": 99})
    with pytest.raises(FichierInvalide, match="version plus récente"):
        format_natif.ouvrir(chemin)


def test_type_depuis_extension() -> None:
    assert format_natif.type_depuis_extension(Path("a.CAOA")) == TypeDocument.ASSEMBLAGE
    assert format_natif.type_depuis_extension(Path("a.txt")) is None


# --- Sauvegarde automatique et récupération ---


def test_recuperation_apres_fermeture_inattendue(tmp_path: Path) -> None:
    dossier = tmp_path / "recuperation"
    origine = tmp_path / "Support.caop"
    document = Document(TypeDocument.PIECE, "Support")
    format_natif.enregistrer(document, origine)
    document.renommer("Support modifié")  # travail non enregistré
    recuperation.sauvegarder(document, dossier)
    assert origine.exists() and format_natif.ouvrir(origine).nom == "Support"  # pas écrasé

    # … le logiciel s'arrête brutalement ; au lancement suivant :
    trouves = recuperation.lister(dossier)
    assert [(t.nom, t.chemin_origine) for t in trouves] == [("Support modifié", origine)]
    recupere = recuperation.recuperer(trouves[0])
    assert recupere.nom == "Support modifié"
    assert recupere.chemin == origine
    assert recupere.modifie  # à enregistrer pour garder le travail récupéré
    assert recuperation.lister(dossier) == []  # copie effacée


def test_fermeture_normale_efface_la_copie(tmp_path: Path) -> None:
    document = Document(TypeDocument.ASSEMBLAGE, "Bride")
    recuperation.sauvegarder(document, tmp_path)
    assert len(recuperation.lister(tmp_path)) == 1
    recuperation.supprimer(document, tmp_path)
    assert recuperation.lister(tmp_path) == []


def test_copies_illisibles_ignorees(tmp_path: Path) -> None:
    (tmp_path / "abime.caop").write_bytes(b"\x00\x01")
    (tmp_path / "notes.txt").write_text("rien", encoding="utf-8")
    assert recuperation.lister(tmp_path) == []
    assert recuperation.lister(tmp_path / "inexistant") == []
