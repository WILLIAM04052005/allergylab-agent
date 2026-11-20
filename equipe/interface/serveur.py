"""Une page web pour explorer les données et poser une question à l'agent, sur ta machine.

    uv run python -m equipe.interface.serveur

puis ouvre http://127.0.0.1:8000 dans ton navigateur. Ctrl+C arrête le serveur.
Après une modification de ce fichier ou de donnees.py, il faut le relancer.

Démo en ligne, ouverte depuis n'importe quel appareil, par un tunnel Cloudflare :

    uv run python -m equipe.interface.serveur 8000 --tunnel
    cloudflared tunnel --url http://localhost:8000      (dans un second terminal)

Le serveur reste sur 127.0.0.1 : seul le tunnel l'atteint, pas le réseau local.
L'agent tourne toujours sur cette machine, à l'identique de `uv run kit agent`.
--tunnel accepte en plus les adresses *.trycloudflare.com, et plafonne le nombre
de questions par heure, parce que n'importe qui ayant le lien dépense la clé.

Hébergement permanent (Render, conteneur Docker : voir le Dockerfile à la racine) :

    python -m equipe.interface.serveur --en-ligne

--en-ligne écoute sur toutes les interfaces, sur le port donné par la variable
PORT, et accepte l'adresse publique de la plateforme. La clé vient de la variable
ALLERGYLAB_CLE, jamais d'un fichier du dépôt. Les plafonds se règlent avec
ALLERGYLAB_QUESTIONS_HEURE et ALLERGYLAB_QUESTIONS_JOUR.

À gauche, des graphiques comptés par equipe/interface/donnees.py, sans appel au
modèle. À droite, l'agent : la page passe par le même chemin que
`uv run kit agent`, donc même agent, même contrat de réponse, même trace écrite
dans traces/. Aucune dépendance ajoutée : le serveur vient de la bibliothèque
standard de Python, la page n'appelle aucun site extérieur.
"""

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from equipe.interface import donnees
from kit import cli, modele, question
from kit.donnees import RACINE

DOSSIER = Path(__file__).parent
TRACES = RACINE / "traces" / "appels"
# Les seuls fichiers que le serveur accepte d'envoyer, et leur nature.
FICHIERS = {
    "/": ("page.html", "text/html"),
    "/style.css": ("style.css", "text/css"),
    "/outils.js": ("outils.js", "text/javascript"),
    "/explorateur.js": ("explorateur.js", "text/javascript"),
    "/agent.js": ("agent.js", "text/javascript"),
}
# 127.0.0.1 : le serveur ne répond qu'à cette machine. L'agent exécute du code
# et dépense la cagnotte de l'équipe : il ne s'ouvre pas au réseau.
EN_LIGNE = "--en-ligne" in sys.argv  # hébergement permanent, derrière le proxy https de la plateforme
TUNNEL = "--tunnel" in sys.argv  # démo depuis ce PC, par un tunnel Cloudflare
HOTE = "0.0.0.0" if EN_LIGNE else "127.0.0.1"
ARGUMENTS = [argument for argument in sys.argv[1:] if not argument.startswith("--")]
PORT = int(ARGUMENTS[0]) if ARGUMENTS else int(os.environ.get("PORT", "8000"))
ORIGINES = (f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}")
DOMAINE_TUNNEL = ".trycloudflare.com"
# En ligne, n'importe qui ayant le lien dépense la clé : au-delà, le serveur refuse.
QUESTIONS_PAR_HEURE = int(os.environ.get("ALLERGYLAB_QUESTIONS_HEURE", "30"))
QUESTIONS_PAR_JOUR = int(os.environ.get("ALLERGYLAB_QUESTIONS_JOUR", "200"))
PUBLIC = EN_LIGNE or TUNNEL
POSEES = []  # instants des questions des dernières 24 heures, pour les plafonds
LONGUEUR_MAX = 2000  # caractères d'une question
NB_HISTORIQUE = 8  # questions passées que la page peut réafficher
# Le kit ne suit qu'une question à la fois : les suivantes attendent leur tour.
UNE_A_LA_FOIS = threading.Lock()


def lire_trace(fichier):
    """Une trace d'appel, avec son chemin dans le dépôt."""
    trace = json.loads(fichier.read_text(encoding="utf-8"))
    trace["trace"] = fichier.relative_to(RACINE).as_posix()
    return trace


def interroger(texte):
    """Pose la question par le kit, puis rend la trace qu'il vient d'écrire."""
    with UNE_A_LA_FOIS:
        modele.journal_neuf()  # dès maintenant : le suivi ne montre jamais les étapes de la question d'avant
        avant = set(TRACES.rglob("*.json"))
        try:
            question.poser(texte)
        except Exception:
            pass  # une erreur imprévue : le kit l'a quand même notée dans la trace
        nouvelles = sorted(set(TRACES.rglob("*.json")) - avant)
    if not nouvelles:
        return {"erreur": "Le kit n'a écrit aucune trace pour cette question."}
    return lire_trace(nouvelles[-1])


def progression():
    """Où en est la question en cours : le code de chaque étape finie, les jetons et le coût jusqu'ici."""
    journal = modele.journal
    return {
        "en_cours": UNE_A_LA_FOIS.locked(),
        "etapes": [etape["code"] for etape in list(journal["etapes"])],
        "jetons": dict(journal["jetons"]),
        "cout_estime": journal["cout_estime"],
    }


def historique():
    """Les dernières questions déjà posées, relues dans traces/ : aucun appel au modèle."""
    fichiers = sorted(TRACES.rglob("*.json"), key=lambda fichier: fichier.name)[-NB_HISTORIQUE:]
    return [lire_trace(fichier) for fichier in fichiers]


class Page(BaseHTTPRequestHandler):
    def envoyer(self, code, contenu, nature):
        corps = contenu.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{nature}; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")  # la page affiche toujours la dernière version des fichiers
        self.end_headers()
        self.wfile.write(corps)

    def json(self, contenu, code=200):
        self.envoyer(code, json.dumps(contenu, ensure_ascii=False), "application/json")

    def refuser(self, code, message):
        self.json({"erreur": message}, code)

    def etranger(self):
        """Vrai si la demande ne s'adresse pas à cette machine sous son propre nom (ou à son tunnel)."""
        hote = self.headers.get("Host") or ""
        if EN_LIGNE and hote:
            return False  # la plateforme ne transmet que les demandes faites à son adresse publique
        if TUNNEL and hote.endswith(DOMAINE_TUNNEL):
            return False
        return hote not in (origine.removeprefix("http://") for origine in ORIGINES)

    def origines_admises(self):
        hote = self.headers.get("Host") or ""
        public = EN_LIGNE or (TUNNEL and hote.endswith(DOMAINE_TUNNEL))
        return ORIGINES + ((f"https://{hote}",) if public and hote else ())

    def do_GET(self):
        if self.etranger():
            self.refuser(403, "Cette demande ne vient pas de la page de l'agent.")
        elif self.path in FICHIERS:
            nom, nature = FICHIERS[self.path]
            self.envoyer(200, (DOSSIER / nom).read_text(encoding="utf-8"), nature)
        elif self.path == "/donnees":  # les effectifs des graphiques
            self.json(donnees.resume())
        elif self.path == "/progression":
            self.json(progression())
        elif self.path == "/historique":
            self.json(historique())
        else:
            self.refuser(404, "Cette page n'existe pas.")

    def do_POST(self):
        # Une autre page ouverte dans le navigateur ne doit pas pouvoir faire
        # travailler l'agent : la demande vient de notre page, en JSON, ou elle est refusée.
        origine = self.headers.get("Origin")
        if self.path != "/question" or self.headers.get("Content-Type") != "application/json":
            return self.refuser(404, "Cette adresse n'existe pas.")
        if self.etranger() or (origine and origine not in self.origines_admises()):
            return self.refuser(403, "Cette demande ne vient pas de la page de l'agent.")
        if PUBLIC:
            maintenant = time.monotonic()
            POSEES[:] = [instant for instant in POSEES if maintenant - instant < 86400]
            if sum(maintenant - instant < 3600 for instant in POSEES) >= QUESTIONS_PAR_HEURE:
                return self.refuser(429, f"La démo est limitée à {QUESTIONS_PAR_HEURE} questions par heure. Réessayez plus tard.")
            if len(POSEES) >= QUESTIONS_PAR_JOUR:
                return self.refuser(429, f"La démo est limitée à {QUESTIONS_PAR_JOUR} questions par jour. Réessayez demain.")
        try:
            taille = int(self.headers.get("Content-Length", "0"))
            texte = json.loads(self.rfile.read(min(taille, 4 * LONGUEUR_MAX)))["question"].strip()
        except (ValueError, KeyError, TypeError, AttributeError):
            return self.refuser(400, "La question est illisible.")
        if not texte or len(texte) > LONGUEUR_MAX:
            return self.refuser(400, f"Écrivez une question de {LONGUEUR_MAX} caractères au plus.")
        if PUBLIC:
            POSEES.append(time.monotonic())  # seules les vraies questions comptent dans le plafond
        self.json(interroger(texte))

    def log_message(self, *arguments):
        pass  # le kit affiche déjà chaque question dans le terminal


class Serveur(ThreadingHTTPServer):
    # Sous Windows, deux serveurs peuvent sinon se partager le même port sans erreur :
    # l'ancien continue alors de répondre, avec l'ancienne page.
    allow_reuse_address = False


if __name__ == "__main__":
    cli.regler_console()
    try:
        serveur = Serveur((HOTE, PORT), Page)
    except OSError:
        print(f"Le port {PORT} est déjà pris : un ancien serveur tourne sans doute encore.")
        print(f"Que faire : arrête-le avec Ctrl+C dans son terminal, ou lance celui-ci sur un autre port, par exemple {PORT + 1}.")
        sys.exit(1)
    # Les chiffres des graphiques se calculent ici, une fois, avant d'annoncer l'adresse :
    # la page les reçoit ensuite sans attendre.
    donnees.resume()
    print(f"Interface de l'agent : {ORIGINES[0]}  (Ctrl+C pour arrêter)", flush=True)
    if EN_LIGNE:
        print(f"Mode en ligne : port {PORT}, {QUESTIONS_PAR_HEURE} questions par heure et {QUESTIONS_PAR_JOUR} par jour au plus.", flush=True)
    if TUNNEL:
        print(f"Mode démo en ligne : adresses {DOMAINE_TUNNEL} acceptées, {QUESTIONS_PAR_HEURE} questions par heure au plus.")
        print(f"Dans un second terminal : cloudflared tunnel --url http://localhost:{PORT}")
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("Serveur arrêté.")
