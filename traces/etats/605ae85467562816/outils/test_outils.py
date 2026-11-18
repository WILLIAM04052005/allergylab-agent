"""Tests des outils, sans le modèle ni la clé : uv run python -m pytest equipe -q"""

from equipe.outils.chercher_colonnes import chercher_colonnes
from equipe.outils.commun import CODES
from equipe.outils.decrire_colonne import decrire_colonne
from equipe.outils.repartition import repartition
from equipe.outils.resume_numerique import resume_numerique
from kit.donnees import colonnes


def test_decrire_donne_le_codage_du_sexe():
    assert "1 = Masculin" in decrire_colonne("Gender") and "0 = Féminin" in decrire_colonne("Gender")


def test_toutes_les_colonnes_cliniques_ont_une_fiche():
    assert sorted(colonnes().query("bloc == 'clinique'")["colonne"]) == sorted(CODES)


def test_repartition_exclut_les_9():
    texte = repartition("Rural_or_urban_area")
    assert "2980 non renseignés" in texte and "1 = Urbain : 966 (74,8 %)" in texte


def test_repartition_decoupe_les_cellules_a_plusieurs_codes():
    assert "la somme des pourcentages peut dépasser 100 %" in repartition("Treatment_of_athsma")


def test_condition():
    assert "Age (condition : Chip_Type=ALEX) : 1139 patients" in resume_numerique("Age", "Chip_Type=ALEX")


def test_dosage_ne_garde_que_les_puces_qui_mesurent():
    texte = resume_numerique("Act_d_8")
    assert "1139 patients d'autres puces exclus" in texte and "valeur(s) à -1" in texte


def test_refus_et_messages_qui_disent_quoi_faire():
    assert "Colonnes proches : Gender" in repartition("Gendre")
    assert "Opérateurs admis" in repartition("Gender", "Age=>3")
    assert "utilise repartition" in resume_numerique("Gender")
    assert "utilise resume_numerique" in repartition("Ara_h_2")
    assert repartition("Patient_ID").startswith("Refusé")
    assert "impossible de conclure" in repartition("Gender", "Age>200")


def test_chercher_colonnes():
    assert "Ara_h_2" in chercher_colonnes("ara_h")
    assert "Rural_or_urban_area" in chercher_colonnes("")


def test_sorties_courtes():
    for nom in colonnes()["colonne"]:
        for texte in (decrire_colonne(nom), repartition(nom), resume_numerique(nom)):
            assert len(texte) < 2000
