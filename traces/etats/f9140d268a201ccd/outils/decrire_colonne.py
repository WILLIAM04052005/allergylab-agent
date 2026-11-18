"""Outil : dire ce que veut dire une colonne, d'après le dictionnaire officiel.

Sans lui, l'agent devine que 1 = homme, ou s'abstient faute de connaître le codage.
"""

from smolagents import tool

from equipe.outils.commun import CODES, ErreurOutil, puces_qui_mesurent, table_colonnes, verifier_colonne


@tool
def decrire_colonne(nom: str) -> str:
    """Explique une colonne : son sens, ses codes, ses valeurs « non renseigné » et les puces qui la mesurent.
    À appeler avant d'interpréter une colonne.

    Args:
        nom: le nom exact de la colonne, par exemple "Gender" ou "Ara_h_2".
    """
    try:
        ligne = verifier_colonne(nom)
    except ErreurOutil as erreur:
        return str(erreur)
    puces = puces_qui_mesurent(nom)
    toutes = [c.removeprefix("puce_") for c in table_colonnes().columns if c.startswith("puce_")]
    absentes = [p for p in toutes if p not in puces]
    lignes = [f"Colonne {nom} (bloc {ligne['bloc']}), renseignée pour les puces : {', '.join(puces)}."]
    if absentes:
        lignes.append(f"Jamais mesurée sur : {', '.join(absentes)} ; ces patients sont exclus des calculs.")

    if ligne["bloc"] == "dosage":
        lignes.append(
            "Dosage d'IgE spécifiques d'un composant allergénique. Une case vide n'est pas forcément un résultat négatif. "
            "Le dictionnaire officiel ne donne ni unité ni seuil de positivité ; "
            "les puces ISAC et ALEX n'utilisent pas forcément la même échelle."
        )
        return "\n".join(lignes)

    fiche = CODES.get(nom, {})
    lignes.append(f"Sens : {fiche.get('sens', 'aucune description')}")
    lignes.append(f"Correspondance avec le dictionnaire officiel : {fiche.get('correspondance', 'absente')}.")
    if "codes" in fiche:
        lignes.append("Codes : " + " ; ".join(f"{code} = {sens}" for code, sens in fiche["codes"].items()) + ".")
    if "manquant" in fiche:
        lignes.append(f"ATTENTION : {fiche['manquant']} veut dire non renseigné ; les outils l'excluent d'eux-mêmes.")
    return "\n".join(lignes)
