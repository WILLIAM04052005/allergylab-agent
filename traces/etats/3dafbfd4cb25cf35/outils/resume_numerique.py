"""Outil : résumer une colonne de nombres (âge, dosage d'un allergène).

Pour un dosage, il ne garde que les patients des puces qui mesurent l'allergène.
"""

from smolagents import tool

from equipe.outils.commun import (
    CODES,
    ErreurOutil,
    appliquer_condition,
    pourcent,
    puces_qui_mesurent,
    tableau,
    verifier_colonne,
)


def nombre(x):
    return f"{x:.2f}".rstrip("0").rstrip(".").replace(".", ",")


@tool
def resume_numerique(colonne: str, condition: str = "") -> str:
    """Résume une colonne de nombres : effectif, manquants, moyenne, médiane, minimum, maximum.
    Pour un allergène (dosage), donne aussi combien de patients ont une valeur > 0, en ne gardant
    que les puces qui le mesurent. Pour une colonne codée (Gender, Rural_or_urban_area…), utilise repartition.

    Args:
        colonne: le nom exact de la colonne, par exemple "Age" ou "Ara_h_2".
        condition: filtre facultatif, « colonne opérateur valeur » séparés par « ; », par exemple "Chip_Type=ALEX".
    """
    try:
        ligne = verifier_colonne(colonne)
        if "codes" in CODES.get(colonne, {}) or ligne["lecture"] != "nombre":
            return f"{colonne} est une colonne codée ou textuelle : utilise repartition({colonne!r})."
        table, filtre = appliquer_condition(tableau(), condition)
    except ErreurOutil as erreur:
        return str(erreur)

    lignes = []
    if ligne["bloc"] == "dosage":
        puces = puces_qui_mesurent(colonne)
        hors = int((~table["Chip_Type"].isin(puces)).sum())
        table = table[table["Chip_Type"].isin(puces)]
        lignes.append(f"Allergène mesuré sur : {', '.join(puces)} ; {hors} patients d'autres puces exclus.")
    valeurs = table[colonne].dropna()
    lignes.insert(0, f"{colonne}{filtre} : {len(table)} patients, {len(valeurs)} valeurs, {len(table) - len(valeurs)} manquantes.")
    negatives = int((valeurs < 0).sum())
    if ligne["bloc"] == "dosage" and negatives:
        # -1 n'a pas de sens pour un dosage, et le dictionnaire ne le documente pas.
        valeurs = valeurs[valeurs >= 0]
        lignes.append(f"{negatives} valeur(s) à -1, sens non documenté : exclues des calculs.")
    if valeurs.empty:
        return "\n".join(lignes + ["Aucune valeur : impossible de conclure."])
    lignes.append(
        f"Moyenne {nombre(valeurs.mean())} ; médiane {nombre(valeurs.median())} ; "
        f"min {nombre(valeurs.min())} ; max {nombre(valeurs.max())}."
    )
    if ligne["bloc"] == "dosage":
        positifs = int((valeurs > 0).sum())
        lignes.append(
            f"Valeur > 0 : {positifs} patients ({pourcent(positifs, len(valeurs))} des valeurs). "
            "Aucun seuil de positivité officiel : « > 0 » n'est pas « allergique »."
        )
    if len(valeurs) < 30:
        lignes.append("ATTENTION : moins de 30 valeurs ; réponds, en signalant la fragilité.")
    return "\n".join(lignes)
