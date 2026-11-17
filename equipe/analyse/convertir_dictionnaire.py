"""Transcrit le dictionnaire officiel (donnees/acc-dictionnaire-final.xls) en CSV.

Le kit ne sait pas lire le format .xls. Ce script le lit avec xlrd, emprunté le
temps d'une commande, sans l'ajouter aux dépendances du projet :

    uv run --with xlrd python equipe/analyse/convertir_dictionnaire.py

Il écrit equipe/outils/dictionnaire_officiel.csv. Il recopie, il n'interprète
pas : les rubriques gardent leur titre français, tel que publié.

Cette transcription sert de référence : elle permet de vérifier que
equipe/outils/codes.toml, recopié à la main, dit la même chose que le
dictionnaire officiel.
"""

import csv
from pathlib import Path

import xlrd

RACINE = Path(__file__).parents[2]
SOURCE = RACINE / "donnees" / "acc-dictionnaire-final.xls"
SORTIE = RACINE / "equipe" / "outils" / "dictionnaire_officiel.csv"

# La feuille range ses rubriques côte à côte : chacune commence à l'une de ces colonnes.
# La première occupe trois colonnes (libellé, abrégé, code), les autres deux (libellé, code).
DEBUTS = (0, 4, 7, 10, 13, 16, 19, 22, 25)
# Une ligne de titre porte le nom de la rubrique, puis l'un de ces deux mots.
TITRES = ("Abrégé", "Anonyme")


def texte(cellule):
    """Le contenu d'une cellule, en texte. Excel range 9 sous la forme 9.0 : on rend « 9 »."""
    valeur = cellule.value
    if isinstance(valeur, float) and valeur == int(valeur):
        return str(int(valeur))
    return str(valeur).strip()


feuille = xlrd.open_workbook(SOURCE).sheet_by_index(0)
lignes = []
for debut in DEBUTS:
    largeur = 3 if debut == 0 else 2
    rubrique = None
    for numero in range(feuille.nrows):
        cellules = [texte(feuille.cell(numero, debut + k)) for k in range(largeur)]
        if not any(cellules):
            continue
        if cellules[1] in TITRES:
            rubrique = cellules[0]
        elif rubrique:  # avant la première rubrique, il n'y a que le titre de la feuille
            libelle, abrege, code = cellules if largeur == 3 else (cellules[0], "", cellules[1])
            lignes.append([rubrique, libelle, abrege, code])

with open(SORTIE, "w", encoding="utf-8", newline="") as sortie:
    ecrivain = csv.writer(sortie, lineterminator="\n")
    ecrivain.writerow(["rubrique", "libelle", "abrege", "code"])
    ecrivain.writerows(lignes)

print(f"{len(lignes)} lignes écrites dans {SORTIE.relative_to(RACINE).as_posix()}")
