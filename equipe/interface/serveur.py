"""Une page web pour explorer les données et poser une question à l'agent, sur ta machine.

    uv run python -m equipe.interface.serveur

puis ouvre http://127.0.0.1:8000 dans ton navigateur. Ctrl+C arrête le serveur.
Après une modification de ce fichier ou de donnees.py, il faut le relancer.

À gauche, des graphiques comptés par equipe/interface/donnees.py, sans appel au
modèle. À droite, l'agent : la page passe par le même chemin que
`uv run kit agent`, donc même agent, même contrat de réponse, même trace écrite
dans traces/. Aucune dépendance ajoutée : le serveur vient de la bibliothèque
standard de Python, la page n'appelle aucun site extérieur.
"""

import json
import sys
import threading
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
HOTE = "127.0.0.1"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
ORIGINES = (f"http://{HOTE}:{PORT}", f"http://localhost:{PORT}")
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
        """Vrai si la demande ne s'adresse pas à cette machine sous son propre nom."""
        return self.headers.get("Host") not in (origine.removeprefix("http://") for origine in ORIGINES)

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
        if self.etranger() or (origine and origine not in ORIGINES):
            return self.refuser(403, "Cette demande ne vient pas de la page de l'agent.")
        try:
            taille = int(self.headers.get("Content-Length", "0"))
            texte = json.loads(self.rfile.read(min(taille, 4 * LONGUEUR_MAX)))["question"].strip()
        except (ValueError, KeyError, TypeError, AttributeError):
            return self.refuser(400, "La question est illisible.")
        if not texte or len(texte) > LONGUEUR_MAX:
            return self.refuser(400, f"Écrivez une question de {LONGUEUR_MAX} caractères au plus.")
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
    print(f"Interface de l'agent : {ORIGINES[0]}  (Ctrl+C pour arrêter)")
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("Serveur arrêté.")
