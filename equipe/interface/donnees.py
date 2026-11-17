"""Les chiffres que la page montre en graphiques : des effectifs, jamais une ligne de patient.

Ils sont comptés avec les règles des outils de l'agent (equipe/outils/commun.py),
pour que la page et l'agent donnent les mêmes nombres : non renseignés exclus,
cellules à plusieurs codes découpées, dosages lus sur les seules puces qui les
mesurent, valeurs à -1 écartées.
"""

from functools import cache

from equipe.outils.commun import CODES, code_manquant, codes_de, libelle, puces_qui_mesurent, tableau
from kit.donnees import COLONNE_PUCE, NB_CLINIQUES

PUCES = ("ISAC_V1", "ISAC_V2", "ALEX")
# Les colonnes cliniques dont le dictionnaire donne plusieurs codes.
COLONNES_CODEES = [nom for nom, fiche in CODES.items() if len(fiche.get("codes", {})) > 1]
LARGEUR_CLASSE = 5  # années par classe d'âge
DERNIERE_CLASSE = 90  # la dernière classe réunit « 90 ans et plus »
MINIMUM = 30  # patients mesurés ; en dessous, la page n'affiche pas de part pour un dosage


def ages(table):
    valeurs = table["Age"].dropna()
    debuts = (valeurs.clip(upper=DERNIERE_CLASSE) // LARGEUR_CLASSE * LARGEUR_CLASSE).astype(int).value_counts()
    return {
        "renseignes": len(valeurs),
        "mediane": float(valeurs.median()) if len(valeurs) else None,
        "classes": [
            {"de": debut, "patients": int(debuts.get(debut, 0))}
            for debut in range(0, DERNIERE_CLASSE + 1, LARGEUR_CLASSE)
        ],
    }


def mois(table):
    """Les patients par mois de prélèvement, de janvier à décembre."""
    comptes = table["Blood_Month_sample"].dropna().astype(int).value_counts()
    return [int(comptes.get(numero, 0)) for numero in range(1, 13)]


def variable(table, colonne):
    """La répartition d'une colonne codée, comptée comme l'outil repartition."""
    fiche, manquant = CODES[colonne], code_manquant(colonne)
    listes = table[colonne].map(codes_de)
    renseignes = listes[listes.map(lambda codes: bool(codes) and codes != [manquant])]
    comptes = renseignes.explode().value_counts()
    return {
        "colonne": colonne,
        "rubrique": fiche["rubrique"],
        "sens": fiche["sens"],
        "correspondance": fiche["correspondance"],
        "renseignes": len(renseignes),
        "plusieurs": bool((renseignes.map(len) > 1).any()),
        "codes": [
            {"code": code, "libelle": libelle(colonne, code), "patients": int(nombre)}
            for code, nombre in comptes.items()
        ],
    }


def colonnes_dosage():
    return list(tableau().columns[NB_CLINIQUES:])


def dosages(table):
    """Pour chaque colonne de dosage, dans l'ordre du fichier : patients mesurés, et patients au-dessus de zéro."""
    mesures, non_nuls = [], []
    for colonne in colonnes_dosage():
        valeurs = table.loc[table[COLONNE_PUCE].isin(puces_qui_mesurent(colonne)), colonne].dropna()
        valeurs = valeurs[valeurs >= 0]  # -1 : sens non documenté
        mesures.append(len(valeurs))
        non_nuls.append(int((valeurs > 0).sum()))
    return {"mesures": mesures, "non_nuls": non_nuls}


def tranche(table):
    return {
        "patients": len(table),
        "age": ages(table),
        "mois": mois(table),
        "variables": [variable(table, colonne) for colonne in COLONNES_CODEES],
        "dosages": dosages(table),
    }


@cache
def resume():
    """Tout ce que la page affiche : une tranche pour l'ensemble, une par puce. Calculé une seule fois."""
    complet = tableau()
    tranches = {"Toutes": tranche(complet)}
    for puce in PUCES:
        tranches[puce] = tranche(complet[complet[COLONNE_PUCE] == puce])
    return {
        "puces": [{"nom": puce, "patients": tranches[puce]["patients"]} for puce in PUCES],
        "dosages": colonnes_dosage(),  # les noms, dans l'ordre des listes de chaque tranche
        "minimum": MINIMUM,
        "tranches": tranches,
    }
