"""L'agent de l'équipe. Le kit n'en appelle qu'une fonction : repondre(question).

C'est un CodeAgent de smolagents : à chaque étape, le modèle écrit du code
Python, et ce code s'exécute sur ta machine. Avant de modifier ce fichier,
lis la rubrique « Ce qu'un agent ouvert peut faire » du README.
"""

import importlib.resources
from pathlib import Path

import yaml
from smolagents import CodeAgent

from equipe.outils.chercher_colonnes import chercher_colonnes
from equipe.outils.decrire_colonne import decrire_colonne
from equipe.outils.repartition import repartition
from equipe.outils.resume_numerique import resume_numerique
from kit import modele, reponse
from kit.donnees import charger

CONSIGNE = (Path(__file__).parent / "consigne.md").read_text(encoding="utf-8")

# Le prompt système de smolagents fait près de 10 000 caractères d'exemples sans
# rapport avec nos données, renvoyés au modèle à chaque étape. On le remplace par
# un gabarit court (equipe/outils/prompt_systeme.md) ; le reste ne change pas.
GABARITS = yaml.safe_load(importlib.resources.files("smolagents.prompts").joinpath("code_agent.yaml").read_text())
GABARITS["system_prompt"] = (Path(__file__).parent / "outils" / "prompt_systeme.md").read_text(encoding="utf-8")

# Accès aux données.
# False (fermé) : l'agent n'atteint les données que par les outils. Aucune ligne
#   de patient n'est envoyée au modèle, et le prompt est plus court.
# True (ouvert) : l'agent reçoit aussi le tableau complet et peut importer pandas.
OUVERT = False

# Plafond de jetons écrits par le modèle à chaque étape. Sans lui, une question
# simple a déjà coûté 16 526 jetons de sortie (trace du 16/11, 13h31).
JETONS_SORTIE_MAX = 1500


def repondre(question):
    modele_kit = modele.ModeleKit()  # le modèle de kit/reglages.toml
    modele_kit.kwargs["max_tokens"] = JETONS_SORTIE_MAX
    agent = CodeAgent(
        model=modele_kit,
        tools=[chercher_colonnes, decrire_colonne, repartition, resume_numerique],
        prompt_templates=GABARITS,
        instructions=reponse.consigne(CONSIGNE),  # ta consigne, puis le format de réponse du kit
        max_steps=modele.REGLAGES["agent"]["etapes_max"],
        max_print_outputs_length=modele.REGLAGES["agent"]["sortie_max"],
        step_callbacks=[modele.noter_etape],  # recopie chaque étape dans la trace
        # Accès aux données : le code écrit par le modèle peut importer pandas.
        additional_authorized_imports=["pandas"] if OUVERT else [],
    )
    return agent.run(
        question,
        # Accès aux données : le code écrit par le modèle reçoit le tableau complet, sous le nom tableau.
        additional_args={"tableau": charger()} if OUVERT else None,
    )
