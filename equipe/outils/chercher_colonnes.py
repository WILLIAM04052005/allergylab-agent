"""Outil : trouver le nom exact des colonnes, sans recevoir le tableau."""

from smolagents import tool

from equipe.outils.commun import table_colonnes, tableau

MAX_NOMS = 40


@tool
def chercher_colonnes(motif: str) -> str:
    """Liste les colonnes dont le nom contient le motif (sans tenir compte des majuscules).
    Motif vide : les 15 colonnes cliniques. Les allergènes suivent la nomenclature officielle,
    par exemple Ara_h_2 pour l'arachide, Bet_v_1 pour le bouleau, Der_p_1 pour l'acarien.

    Args:
        motif: un morceau de nom, par exemple "ara_h" ou "treatment" ; vide pour les colonnes cliniques.
    """
    table = table_colonnes()
    table = table[table.index.isin(tableau().columns)]  # seulement les colonnes de la table en cours
    if not motif.strip():
        noms = table.index[table["bloc"] == "clinique"].tolist()
        return "Colonnes cliniques : " + ", ".join(noms) + f". Puis {(table['bloc'] == 'dosage').sum()} colonnes de dosage."
    noms = [nom for nom in table.index if motif.strip().lower() in nom.lower()]
    if not noms:
        return f"Aucune colonne ne contient {motif!r}. Essaie un motif plus court, par exemple les 3 premières lettres."
    suite = f" (et {len(noms) - MAX_NOMS} autres : précise le motif)" if len(noms) > MAX_NOMS else ""
    return f"{len(noms)} colonne(s) : " + ", ".join(noms[:MAX_NOMS]) + suite + "."
