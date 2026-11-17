"""Donne à l'agent le dictionnaire officiel des données, rubrique par rubrique.

Le dictionnaire publié (donnees/acc-dictionnaire-final.xls) est dans un format
que le kit ne lit pas. dictionnaire_officiel.csv, à côté de ce fichier, en est
la transcription ; equipe/analyse/convertir_dictionnaire.py la refait.

Pour brancher l'outil, dans equipe/agent.py :
    from equipe.outils.dictionnaire import codes_officiels
puis tools=[codes_officiels] dans l'appel à CodeAgent.
"""

import csv
from pathlib import Path

from smolagents import tool

FICHIER = Path(__file__).parent / "dictionnaire_officiel.csv"


def lire_rubriques():
    """Rend, pour chaque rubrique, la liste de ses codes, chacun en une phrase courte."""
    rubriques = {}
    with open(FICHIER, encoding="utf-8", newline="") as fichier:
        for ligne in csv.DictReader(fichier):
            code = ligne["libelle"]
            if ligne["abrege"]:
                code += f" (abrégé {ligne['abrege']})"
            if ligne["code"]:
                code += f" = {ligne['code']}"
            rubriques.setdefault(ligne["rubrique"], []).append(code)
    return rubriques


@tool
def codes_officiels(rubrique: str) -> str:
    """Rend les codes d'une rubrique du dictionnaire officiel des données, tel que son éditeur l'a publié.

    Les rubriques sont en français. Le dictionnaire ne donne pas le nom des colonnes du tableau.

    Args:
        rubrique: le titre d'une rubrique ou un morceau de ce titre, par exemple "habitat". Un texte vide rend la liste des rubriques.
    """
    rubriques = lire_rubriques()
    cherche = rubrique.strip().casefold()
    trouvees = [titre for titre in rubriques if cherche and cherche in titre.casefold()]
    # Rien trouvé : on rend les titres, pour que le modèle choisisse au lieu d'inventer.
    if not trouvees:
        return "Rubriques du dictionnaire officiel : " + " ; ".join(rubriques)
    return "\n".join(f"{titre} : " + " ; ".join(rubriques[titre]) for titre in trouvees)
