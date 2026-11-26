"""Alerte ntfy quand une résidence ARPEJ surveillée n'affiche plus « Aucun logement »."""
import json
import os
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

# Ajoutez ici les pages des résidences parisiennes qui vous intéressent.
RESIDENCES = [RESIDENCES = [
    "https://www.arpej.fr/en/residence/nicolas-appert/",  # Ivry, M7
    "https://www.arpej.fr/en/residence/porte-ditalie/",  # Kremlin-Bicêtre, M7
    "https://www.arpej.fr/en/residence/paris/",  # EOLE, Paris 19e 
]
    
STATE = Path("state.json")


class Textes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.textes, self.ignore = [], False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.ignore = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.ignore = False

    def handle_data(self, data):
        t = " ".join(data.split())
        if t and not self.ignore:
            self.textes.append(t)


def disponibilite(html):
    p = Textes()
    p.feed(html)
    for i, t in enumerate(p.textes[:-1]):
        if t.rstrip(" :").lower() in ("disponibilité", "availability"):
            return p.textes[i + 1]
    raise ValueError("champ Disponibilité introuvable (page modifiée ?)")


def est_libre(statut):
    s = statut.lower()
    return not (s.startswith("aucun") or s.startswith("no "))


def telecharger(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def notifier(message, url):
    req = urllib.request.Request(
        "https://ntfy.sh/" + os.environ["NTFY_TOPIC"],
        data=message.encode(),
        headers={"Title": "Logement ARPEJ", "Priority": "high", "Click": url},
    )
    urllib.request.urlopen(req, timeout=30).close()


def main():
    if "--test" in sys.argv:
        notifier("Test : les notifications fonctionnent.", "https://www.arpej.fr")
        return
    etat = json.loads(STATE.read_text()) if STATE.exists() else {}
    erreurs = 0
    for url in RESIDENCES:
        try:
            statut = disponibilite(telecharger(url))
            print(url, "->", statut)
            # Une seule alerte par changement de statut.
            if est_libre(statut) and etat.get(url) != statut:
                notifier(f"{statut}\n{url}", url)
            etat[url] = statut
        except Exception as e:
            print(url, "ERREUR", e)
            erreurs += 1
    STATE.write_text(json.dumps(etat, indent=2, ensure_ascii=False))
    if erreurs:
        sys.exit(1)  # GitHub signale alors l'échec


if __name__ == "__main__":
    main()
