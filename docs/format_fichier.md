# Format de fichier natif

> Exigences DOC-01, DOC-07, TEC-10. Version du format : **1** (logiciel 0.1.0). Mis à jour à chaque changement de format.

## Extensions

| Document | Extension |
| --- | --- |
| Pièce | `.caop` |
| Assemblage | `.caoa` |
| Mise en plan | `.caom` |

Extensions validées le 2026-10-31.

## Contenu

Un document est une **archive ZIP** (on peut l'ouvrir avec n'importe quel outil ZIP pour l'inspecter). Elle contient :

| Élément | Contenu |
| --- | --- |
| `document.json` | Description du document, en texte (JSON, UTF-8) |
| `geometrie/*.brep` | Formes au format B-Rep d'OpenCascade (à partir du lot 3) |

### `document.json`

```json
{
  "application": "CAO simplifiée 0.1.0",
  "contenu": {},
  "enregistre_le": "2026-10-31T14:05:12+00:00",
  "format": "cao-simplifiee",
  "nom": "Équerre",
  "type": "piece",
  "version_format": 1
}
```

| Clé | Sens |
| --- | --- |
| `format` | Toujours `cao-simplifiee` : permet de reconnaître un fichier du logiciel |
| `version_format` | Numéro de version du format, entier, augmenté à chaque changement incompatible |
| `application` | Logiciel et version qui ont écrit le fichier (information) |
| `enregistre_le` | Date et heure d'enregistrement, temps universel, ISO 8601 |
| `type` | `piece`, `assemblage` ou `mise_en_plan` |
| `nom` | Nom du document au moment de l'enregistrement (à l'ouverture, le nom du fichier fait foi) |
| `contenu` | Données propres au type : esquisses et fonctions (lot 2-3), composants et contraintes (lot 4), vues et annotations (lot 5) |
| `recuperation` | Seulement dans les copies de sauvegarde automatique : `chemin_origine` du document |

## Règles

- **Identique sous Windows et Linux** : UTF-8, fins de ligne `\n`, clés triées, aucun chemin absolu dans un document enregistré (les références entre documents seront relatives, DOC-04).
- **Écriture sûre** : le logiciel écrit d'abord `nom.caop.tmp`, puis le renomme. Un plantage pendant l'enregistrement laisse l'ancien fichier intact.
- **Compatibilité ascendante** : la version N+1 du logiciel lit les fichiers de version de format ≤ N+1. Un fichier d'une version plus récente est refusé avec un message clair.

## Sauvegarde automatique

Toutes les 5 minutes, chaque document modifié est copié dans le dossier de récupération du système (Windows : `%APPDATA%\CAO simplifiée\recuperation` ; Linux : `~/.local/share/CAO simplifiée/recuperation`). Les copies portent un identifiant de séance pour nom. Elles sont effacées à la fermeture normale du document. S'il en reste au lancement, le logiciel propose de les récupérer.
