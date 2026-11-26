"""Alerte ntfy quand un nouveau logement Crous apparaît dans votre recherche."""
import json
import os
import re
import urllib.request
from pathlib import Path

# Zone : Paris + Le Kremlin-Bicêtre (ouest_nord_est_sud).
URL = "https://trouverunlogement.lescrous.fr/tools/48/search?bounds=2.2241_48.9022_2.4698_48.8050"
STATE = Path("state_crous.json")


def telecharger(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def logements(html):
    liens = set(re.findall(r"/tools/\d+/accommodations/\d+", html))
    if not liens and "aucun logement trouvé" not in html.lower():
        raise SystemExit("ERREUR : page non reconnue (surcharge ou site modifié)")
    return sorted("https://trouverunlogement.lescrous.fr" + l for l in liens)


def tous_les_logements():
    trouves = set(logements(telecharger(URL)))
    for page in range(2, 21):
        suite = set(re.findall(r"/tools/\d+/accommodations/\d+", telecharger(f"{URL}&page={page}")))
        suite = {"https://trouverunlogement.lescrous.fr" + l for l in suite}
        if suite <= trouves:  # page vide ou déjà vue : on s'arrête
            break
        trouves |= suite
    return sorted(trouves)


def notifier(message, url):
    req = urllib.request.Request(
        "https://ntfy.sh/" + os.environ["NTFY_TOPIC"],
        data=message.encode(),
        headers={"Title": "Logement Crous", "Priority": "high", "Click": url},
    )
    urllib.request.urlopen(req, timeout=30).close()


def main():
    actuels = tous_les_logements()
    avant = json.loads(STATE.read_text()) if STATE.exists() else []
    nouveaux = [l for l in actuels if l not in avant]
    print(len(actuels), "logement(s) affiché(s),", len(nouveaux), "nouveau(x)")
    if nouveaux:
        notifier(f"{len(nouveaux)} nouveau(x)\n" + "\n".join(nouveaux[:5]), URL)
    STATE.write_text(json.dumps(actuels))


if __name__ == "__main__":
    main()
