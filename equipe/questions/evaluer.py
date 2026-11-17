"""Fait passer un lot de questions à l'agent et note ses réponses.

    uv run python -m equipe.questions.evaluer lot1
    uv run python -m equipe.questions.evaluer lot1 3     (seulement les 3 premières)

Chaque question passe par le kit (même trace que `uv run kit agent`). À la fin :
une ligne par question, le score, les jetons, le coût, la durée. Le bilan est
ajouté à equipe/analyse/evaluations.csv pour comparer les versions de l'agent.
Coût d'un lot de 17 questions avec Haiku : quelques centimes.
"""

import contextlib
import csv
import io
import json
import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path

from kit.donnees import RACINE
from kit.question import poser

DOSSIER = Path(__file__).parent
JOURNAL = RACINE / "equipe" / "analyse" / "evaluations.csv"


def derniere_trace():
    return max((RACINE / "traces" / "appels").rglob("*.json"), key=lambda p: p.stat().st_mtime)


def juste(reponse, question):
    """Vrai si la réponse correspond à l'attendu."""
    attendu = question["attendu"]
    if reponse is None:
        return False
    if attendu == "abstention":
        return reponse["statut"] == "abstention"
    valeur = reponse["valeur"]
    return reponse["statut"] == "reponse" and isinstance(valeur, (int, float)) and abs(valeur - attendu) <= question.get("tolerance", 0.01)


def main(argv):
    lot = argv[0] if argv else "lot1"
    questions = tomllib.loads((DOSSIER / f"{lot}.toml").read_text(encoding="utf-8"))["question"]
    if len(argv) > 1:
        questions = questions[: int(argv[1])]

    lignes, etat = [], None
    for numero, question in enumerate(questions, 1):
        debut = time.monotonic()
        with contextlib.redirect_stdout(io.StringIO()):  # l'agent est bavard : on ne garde que le bilan
            code = poser(question["texte"])
        duree = time.monotonic() - debut
        trace = json.loads(derniere_trace().read_text(encoding="utf-8"))
        etat = trace["etat"]
        reponse = trace["reponse"] if code == 0 else None
        ok = juste(reponse, question)
        valeur = "erreur" if reponse is None else reponse["statut"] if reponse["statut"] == "abstention" else reponse["valeur"]
        lignes.append((ok, trace["jetons"]["entree"], trace["jetons"]["sortie"], trace["cout_estime"], duree, len(trace["etapes"])))
        print(
            f"{'OK ' if ok else 'NON'} {numero:>2}. {question['texte'][:60]:<60} "
            f"rendu {str(valeur)[:12]:<12} attendu {question['attendu']!s:<10} "
            f"{len(trace['etapes'])} ét. {trace['jetons']['entree']:>6} jetons  {duree:5.1f} s"
        )
        if trace.get("erreur") and "cagnotte" in str(trace["erreur"]).lower():
            print("Cagnotte épuisée : arrêt du lot.")
            break

    n = len(lignes)
    score = sum(l[0] for l in lignes)
    entree, sortie = sum(l[1] for l in lignes), sum(l[2] for l in lignes)
    cout, duree, etapes = sum(l[3] for l in lignes), sum(l[4] for l in lignes), sum(l[5] for l in lignes)
    print(
        f"\nScore {score}/{n}. Par question en moyenne : {entree / n:.0f} jetons en entrée, {sortie / n:.0f} en sortie, "
        f"{etapes / n:.1f} étapes, {duree / n:.1f} s, {cout / n:.5f} $. Coût total : {cout:.4f} $."
    )
    nouveau = not JOURNAL.exists()
    with JOURNAL.open("a", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier)
        if nouveau:
            ecrivain.writerow(["date", "etat", "lot", "questions", "score", "jetons_entree_moy", "jetons_sortie_moy", "etapes_moy", "duree_moy_s", "cout_total_dollars"])
        ecrivain.writerow([datetime.now().isoformat(timespec="minutes"), etat, lot, n, score, round(entree / n), round(sortie / n), round(etapes / n, 1), round(duree / n, 1), round(cout, 5)])
    print(f"Bilan ajouté à {JOURNAL.relative_to(RACINE).as_posix()}.")


if __name__ == "__main__":
    main(sys.argv[1:])
