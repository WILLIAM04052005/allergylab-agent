"""Outil : lire quelques patients précis, colonnes choisies.

Pour les questions sur un patient (« Quel âge a le patient FHB0001 ? ») ou sur
un extrême (« la puce du patient le plus âgé »). Il ne rend jamais plus de
MAX_LIGNES patients ni plus de MAX_COLONNES colonnes : ce qui part vers le
modèle reste minimal.
"""

from smolagents import tool

from equipe.outils.commun import ErreurOutil, appliquer_condition, en_code, tableau, verifier_colonne

MAX_LIGNES = 5
MAX_COLONNES = 6


@tool
def lignes(colonnes: str, condition: str = "", trier_par: str = "", decroissant: bool = True, n: int = 3) -> str:
    """Montre quelques patients, seulement les colonnes demandées. Pour un patient précis
    (condition "Patient_ID=FHB0001") ou un extrême (trier_par "Age" : le plus âgé en premier).
    Signale les ex aequo. Pour compter ou faire une moyenne, utilise plutôt repartition ou resume_numerique.

    Args:
        colonnes: les colonnes à montrer, séparées par des virgules, 6 au plus, par exemple "Patient_ID, Age, Chip_Type".
        condition: filtre facultatif, « colonne opérateur valeur » séparés par « ; », par exemple "Patient_ID=FHB0001".
        trier_par: colonne de tri facultative ; les cases vides sont écartées.
        decroissant: True pour la plus grande valeur d'abord, False pour la plus petite.
        n: nombre de patients à montrer, 5 au plus.
    """
    try:
        noms = [nom.strip() for nom in colonnes.split(",") if nom.strip()]
        if not noms or len(noms) > MAX_COLONNES:
            raise ErreurOutil(f"Donne entre 1 et {MAX_COLONNES} colonnes, séparées par des virgules.")
        for nom in noms + ([trier_par] if trier_par else []):
            verifier_colonne(nom)
        table, filtre = appliquer_condition(tableau(), condition)
    except ErreurOutil as erreur:
        return str(erreur)

    if trier_par:
        table = table.dropna(subset=[trier_par]).sort_values(trier_par, ascending=not decroissant, kind="stable")
    if table.empty:
        return f"Aucun patient{filtre or ''} : la donnée n'existe pas dans la table."
    n = max(1, min(int(n), MAX_LIGNES))
    choisis = table.head(n)
    texte = [f"{len(table)} patient(s){filtre} ; {len(choisis)} montré(s){', tri par ' + trier_par if trier_par else ''} :"]
    for _, patient in choisis.iterrows():
        texte.append("- " + " ; ".join(f"{nom} = {'vide' if patient[nom] != patient[nom] else en_code(patient[nom])}" for nom in noms))
    if trier_par and len(table) > 1 and table[trier_par].iloc[0] == table[trier_par].iloc[1]:
        texte.append(f"ATTENTION : ex aequo en tête sur {trier_par} ; la réponse n'est pas unique.")
    return "\n".join(texte)
