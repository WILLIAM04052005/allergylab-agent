"""Tests des outils, sans le modèle ni la clé : uv run python -m pytest equipe -q"""

from equipe.outils.chercher_colonnes import chercher_colonnes
from equipe.outils.commun import CODES
from equipe.outils.decrire_colonne import decrire_colonne
from equipe.outils.lignes import lignes
from equipe.outils.repartition import repartition
from equipe.outils.resume_numerique import resume_numerique
from kit import donnees
from kit.donnees import colonnes
from kit.evaluer import lire


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
    assert "utilise lignes" in repartition("Patient_ID")
    assert "impossible de conclure" in repartition("Gender", "Age>200")


def test_chercher_colonnes():
    assert "Ara_h_2" in chercher_colonnes("ara_h")
    assert "Rural_or_urban_area" in chercher_colonnes("")


def test_sorties_courtes():
    for nom in colonnes()["colonne"]:
        for texte in (decrire_colonne(nom), repartition(nom), resume_numerique(nom)):
            assert len(texte) < 2000


def test_lignes_patient_precis_et_extreme():
    assert "Age = 21" in lignes("Age", "Patient_ID=FHB0001")
    assert "Patient_ID = XPW0110 ; Chip_Type = ISAC_V1 ; Age = 102" in lignes("Patient_ID, Chip_Type, Age", trier_par="Age", n=1)
    assert "n'existe pas" in lignes("Age", "Patient_ID=ZZZ9999")
    assert "ex aequo" in lignes("Age", trier_par="Age", decroissant=False)
    assert "entre 1 et 6" in lignes("a, b, c, d, e, f, g")


def test_les_outils_suivent_la_table_inventee():
    # uv run kit evaluer --exemple remplace un moment le fichier publié par kit/exemple/mini.csv.
    with donnees.utiliser(donnees.EXEMPLE):
        assert "Age : 12 patients" in resume_numerique("Age") and "Moyenne 33" in resume_numerique("Age")
        assert "Chip_Type = ISAC_V2 ; Age = 70" in lignes("Chip_Type, Age", trier_par="Age", n=1)
        assert "n'existe pas dans la table en cours" in repartition("Ara_h_2")
    assert "Age : 4271 patients" in resume_numerique("Age")


def test_le_lot1_respecte_le_format_du_kit():
    batterie = lire(donnees.RACINE / "equipe" / "questions" / "lot1.toml")
    assert len(batterie.questions) == 21 and batterie.corrige
