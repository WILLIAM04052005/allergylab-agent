"""Outil : compter les patients par valeur d'une colonne clinique, non renseignés exclus.

Il répond en un appel aux questions « combien de… », « quelle proportion de… »,
« quel est le plus fréquent… », avec le dénominateur et les exclus.
"""

from smolagents import tool

from equipe.outils.commun import (
    ErreurOutil,
    appliquer_condition,
    code_manquant,
    codes_de,
    libelle,
    pourcent,
    tableau,
    verifier_colonne,
)

MAX_VALEURS = 25


@tool
def repartition(colonne: str, condition: str = "") -> str:
    """Compte les patients par valeur d'une colonne clinique, avec le libellé de chaque code.
    Exclut d'office les non renseignés (9, 999) et les cases vides, et donne les pourcentages
    sur les seuls patients renseignés. Pour une colonne de dosage, utilise resume_numerique.

    Args:
        colonne: le nom exact d'une colonne clinique, par exemple "Gender" ou "Chip_Type".
        condition: filtre facultatif, « colonne opérateur valeur » séparés par « ; », par exemple "Gender=0; Age>=18".
    """
    try:
        ligne = verifier_colonne(colonne)
        if colonne == "Patient_ID":
            return "Patient_ID est un identifiant : pour un patient précis, utilise lignes."
        if ligne["bloc"] == "dosage":
            return f"{colonne} est une colonne de dosage : utilise resume_numerique({colonne!r})."
        table, filtre = appliquer_condition(tableau(), condition)
    except ErreurOutil as erreur:
        return str(erreur)

    if table.empty:
        return f"Aucun patient ne respecte la condition {condition!r} : impossible de conclure."
    manquant = code_manquant(colonne)
    listes = table[colonne].map(codes_de)
    vides = int((listes.map(len) == 0).sum())
    non_renseignes = int(listes.map(lambda codes: codes == [manquant]).sum()) if manquant else 0
    renseignes = listes[listes.map(lambda codes: bool(codes) and codes != [manquant])]
    comptes = renseignes.explode().value_counts()
    total = len(renseignes)

    lignes = [f"{colonne}{filtre} : {len(table)} patients."]
    exclus = f"Exclus : {vides} vides"
    if manquant:
        exclus += f", {non_renseignes} non renseignés (code {manquant})"
    lignes.append(exclus + f". Restent {total} patients renseignés.")
    if (renseignes.map(len) > 1).any():
        lignes.append("Plusieurs codes possibles par patient : la somme des pourcentages peut dépasser 100 %.")
    for code, nombre in comptes.head(MAX_VALEURS).items():
        nom = libelle(colonne, code)
        lignes.append(f"- {code}{' = ' + nom if nom else ''} : {nombre} ({pourcent(nombre, total)})")
    if len(comptes) > MAX_VALEURS:
        lignes.append(f"… et {len(comptes) - MAX_VALEURS} autres valeurs.")
    if total < 30:
        lignes.append("ATTENTION : moins de 30 patients renseignés ; réponds, en signalant la fragilité.")
    return "\n".join(lignes)
