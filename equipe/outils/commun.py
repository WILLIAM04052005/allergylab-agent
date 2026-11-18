"""Ce que partagent les outils : le tableau, le sens des codes, les conditions.

Ce fichier n'est pas un outil. Les outils l'importent pour ne pas recopier
les mêmes règles :
- les codes « non renseigné » (9, 999) sont exclus des calculs ;
- une cellule clinique peut contenir plusieurs codes (« 1, 3 ») ;
- une colonne de dosage n'est lue que pour les puces qui la mesurent.
"""

import re
import tomllib
from functools import cache
from pathlib import Path

import pandas as pd

from kit import donnees
from kit.donnees import charger, colonnes

CODES = tomllib.loads((Path(__file__).parent / "codes.toml").read_text(encoding="utf-8"))

# Une condition s'écrit « colonne opérateur valeur », plusieurs séparées par « ; ».
# Exemple : "Gender=0; Age>=18". Elle est découpée à la main : jamais d'eval.
FORME_CONDITION = re.compile(r"^\s*(\w+)\s*(!=|>=|<=|=|>|<)\s*(.+?)\s*$")


class ErreurOutil(ValueError):
    """Une demande que l'outil refuse ; le message dit quoi faire à la place."""


@cache
def _charger(chemin):
    return charger(chemin)


def tableau():
    """Le tableau en cours, chargé une seule fois par fichier.

    `uv run kit evaluer --exemple` remplace un moment le fichier publié par la
    table inventée (donnees.en_cours) : on suit ce fichier-là, pas le premier lu.
    """
    return _charger(donnees.en_cours)


@cache
def table_colonnes():
    return colonnes().set_index("colonne")


def verifier_colonne(nom):
    """Rend la ligne de kit/colonnes.csv, ou lève une erreur qui propose des noms proches."""
    table = table_colonnes()
    if nom in table.index and nom in tableau().columns:
        return table.loc[nom]
    if nom in table.index:
        raise ErreurOutil(f"La colonne {nom!r} n'existe pas dans la table en cours.")
    import difflib

    proches = difflib.get_close_matches(nom, table.index.tolist(), n=3)
    conseil = f" Colonnes proches : {', '.join(proches)}." if proches else " Utilise chercher_colonnes."
    raise ErreurOutil(f"Colonne {nom!r} inconnue.{conseil}")


def puces_qui_mesurent(nom):
    ligne = verifier_colonne(nom)
    return [c.removeprefix("puce_") for c in ligne.index if c.startswith("puce_") and ligne[c]]


def en_code(valeur):
    """1.0 -> "1", "deptA" -> "deptA" : la forme sous laquelle codes.toml écrit les codes."""
    if isinstance(valeur, float) and valeur.is_integer():
        return str(int(valeur))
    return str(valeur).strip()


def codes_de(cellule):
    """Les codes d'une cellule : "1, 3" -> ["1", "3"] ; une cellule vide -> []."""
    if pd.isna(cellule):
        return []
    return [en_code(morceau) for morceau in str(cellule).split(",") if morceau.strip()] if isinstance(cellule, str) else [en_code(cellule)]


def code_manquant(nom):
    return CODES.get(nom, {}).get("manquant")


def libelle(nom, code):
    return CODES.get(nom, {}).get("codes", {}).get(code, "")


def appliquer_condition(table, condition):
    """Garde les lignes qui respectent la condition ; rend (table filtrée, texte décrivant le filtre)."""
    if not condition.strip():
        return table, ""
    for morceau in condition.split(";"):
        trouve = FORME_CONDITION.match(morceau)
        if not trouve:
            raise ErreurOutil(f"Condition illisible : {morceau!r}. Forme attendue : \"Gender=0; Age>=18\".")
        nom, operateur, valeur = trouve.groups()
        verifier_colonne(nom)
        if valeur[0] in "=<>!":
            raise ErreurOutil(f"Opérateur illisible dans {morceau!r}. Opérateurs admis : = != >= <= > <.")
        cellules = table[nom]
        if operateur in ("=", "!="):
            garde = cellules.map(lambda c: valeur in codes_de(c))
            garde = garde if operateur == "=" else ~garde & cellules.notna()
        else:
            try:
                seuil = float(valeur)
            except ValueError:
                raise ErreurOutil(f"{operateur} demande un nombre, pas {valeur!r}.") from None
            nombres = pd.to_numeric(cellules, errors="coerce")
            garde = {">": nombres > seuil, "<": nombres < seuil, ">=": nombres >= seuil, "<=": nombres <= seuil}[operateur]
        table = table[garde]
    return table, f" (condition : {condition.strip()})"


def pourcent(part, total):
    return f"{100 * part / total:.1f} %".replace(".", ",") if total else "—"
