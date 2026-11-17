"""Tableau de toutes les questions déjà posées, lu dans traces/appels/.

    uv run python -m equipe.analyse.bilan

Une ligne par trace, puis une moyenne par état de l'agent (une version de
equipe/) : c'est la preuve avant/après pour la restitution. Aucun appel au modèle.
"""

import json
from collections import defaultdict

from kit.donnees import RACINE


def main():
    paretat = defaultdict(list)
    print(f"{'date':<17} {'état':<8} {'question':<48} {'statut':<10} {'ét.':>3} {'entrée':>7} {'sortie':>7} {'coût $':>9} {'durée':>6}")
    for chemin in sorted((RACINE / "traces" / "appels").rglob("*.json")):
        t = json.loads(chemin.read_text(encoding="utf-8"))
        if not t.get("jetons", {}).get("entree"):
            continue  # appel qui n'a pas abouti (clé absente, etc.)
        statut = (t.get("reponse") or {}).get("statut", "erreur")
        print(
            f"{t['horodatage'][:16]:<17} {t['etat'][:8]:<8} {t['question'][:48]:<48} {statut:<10} {len(t['etapes']):>3} "
            f"{t['jetons']['entree']:>7} {t['jetons']['sortie']:>7} {t['cout_estime']:>9.5f} {t.get('duree_s') or 0:>5.1f}s"
        )
        paretat[t["etat"][:8]].append(t)
    print("\nMoyenne par état de l'agent :")
    for etat, liste in paretat.items():
        n = len(liste)
        print(
            f"  {etat} : {n} questions, {sum(len(t['etapes']) for t in liste) / n:.1f} étapes, "
            f"{sum(t['jetons']['entree'] for t in liste) / n:.0f} jetons en entrée, "
            f"{sum(t['jetons']['sortie'] for t in liste) / n:.0f} en sortie, "
            f"{sum(t['cout_estime'] for t in liste) / n:.5f} $, {sum(t.get('duree_s') or 0 for t in liste) / n:.1f} s"
        )


if __name__ == "__main__":
    main()
