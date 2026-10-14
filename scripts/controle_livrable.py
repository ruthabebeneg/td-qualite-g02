# -*- coding: utf-8 -*-
"""Contrôle du dépôt de groupe : avancement des livrables et fichiers interdits.

Usage :
    python3 scripts/controle_livrable.py                  rapport d'avancement ; échoue seulement si un fichier interdit est suivi par git
    python3 scripts/controle_livrable.py --strict S3      échoue aussi s'il reste des marqueurs dans le livrable de la séance S3 (ou DOSSIER)
    python3 scripts/controle_livrable.py --json           sortie JSON (utilisée par le script de suivi de l'enseignant)
    python3 scripts/controle_livrable.py --racine CHEMIN  analyse un autre dépôt (utilisé par le suivi de l'enseignant)
    python3 scripts/controle_livrable.py --init           (enseignant) enregistre le nombre de marqueurs des gabarits vierges

Un marqueur est « [À COMPLÉTER] » ou une cellule de tableau réduite à « … ». Un marqueur restant n'est pas une faute :
un livrable inachevé doit rester visiblement inachevé. Seuls les fichiers interdits font échouer le contrôle.
Bibliothèque standard uniquement."""
import argparse, json, os, re, subprocess, sys

RACINE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__))
GABARITS = os.path.join(DOSSIER_SCRIPT, "gabarits_comptage.json")   # toujours celui de ce script, même avec --racine
LIVRABLES = {
    "S1": "livrables/S1_bronze_profilage.md",
    "S2": "livrables/S2_regles_great_expectations.md",
    "S3": "livrables/S3_integrite_soda.md",
    "S4": "livrables/S4_silver_gold.md",
    "S5": "livrables/S5_certificat_publication.md",
    "JOURNAL": "livrables/JOURNAL_DECISIONS.md",
    "DOSSIER": "livrables/DOSSIER_GO_NOGO.md",
    "EQUIPE": "livrables/00_equipe.md",
    "AVANCEMENT": "AVANCEMENT.md",
}
TAILLE_MAX = 5 * 1024 * 1024
INTERDITS = [
    (re.compile(r"^data/"), "dossier data/ (données du TD)"),
    (re.compile(r"\.(sql\.gz|dump|pem)$"), "sauvegarde ou clé"),
    (re.compile(r"(^|/)\.env$"), "fichier .env"),
    (re.compile(r"(^|/)uncommitted/"), "dossier uncommitted de Great Expectations"),
    (re.compile(r"^(?!livrables/).*\.csv$"), "fichier CSV hors livrables"),
]


def compter(texte):
    marqueurs = len(re.findall(r"\[À COMPLÉTER\]", texte))
    cellules = 0
    for ligne in texte.splitlines():
        if ligne.lstrip().startswith("|"):
            cellules += sum(1 for c in ligne.strip().strip("|").split("|") if c.strip() == "…")
    cases = len(re.findall(r"^- \[ \]", texte, re.M)), len(re.findall(r"^- \[[xX]\]", texte, re.M))
    return marqueurs + cellules, cases


def statuts_avancement(texte):
    n = {"Fait": 0, "En cours": 0, "Bloqué": 0, "À faire": 0}
    total = 0
    for ligne in texte.splitlines():
        cols = [c.strip() for c in ligne.strip().strip("|").split("|")]
        if len(cols) >= 4 and re.match(r"^US-\d+$", cols[1] if len(cols) > 1 else ""):
            total += 1
            if cols[3] in n:
                n[cols[3]] += 1
    n["total"] = total
    return n


def fichiers_suivis():
    try:
        r = subprocess.run(["git", "ls-files"], cwd=RACINE, capture_output=True, text=True, check=True)
        return [f for f in r.stdout.splitlines() if f]
    except Exception:
        sortie = []
        for d, dirs, fs in os.walk(RACINE):
            dirs[:] = [x for x in dirs if x != ".git"]
            for f in fs:
                sortie.append(os.path.relpath(os.path.join(d, f), RACINE).replace(os.sep, "/"))
        return sortie


def interdits(fichiers):
    trouves = []
    for f in fichiers:
        chemin = os.path.join(RACINE, f)
        for motif, raison in INTERDITS:
            if motif.search(f):
                trouves.append((f, raison))
                break
        else:
            if os.path.isfile(chemin) and os.path.getsize(chemin) > TAILLE_MAX:
                trouves.append((f, "fichier de plus de 5 Mo"))
    return trouves


def analyser():
    initial = json.load(open(GABARITS, encoding="utf-8")) if os.path.exists(GABARITS) else {}
    lignes = {}
    for cle, chemin in LIVRABLES.items():
        p = os.path.join(RACINE, chemin)
        if not os.path.exists(p):
            lignes[cle] = {"fichier": chemin, "present": False}
            continue
        restants, (ouvertes, cochees) = compter(open(p, encoding="utf-8").read())
        ini = initial.get(cle)
        taux = None
        if ini:
            taux = round(max(0.0, 1 - restants / ini) * 100, 1)
        lignes[cle] = {"fichier": chemin, "present": True, "marqueurs_restants": restants, "marqueurs_initiaux": ini,
                       "completion_pct": taux, "criteres_coches": cochees, "criteres_total": ouvertes + cochees}
    avance = {}
    p = os.path.join(RACINE, LIVRABLES["AVANCEMENT"])
    if os.path.exists(p):
        avance = statuts_avancement(open(p, encoding="utf-8").read())
    return lignes, avance


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", metavar="CLE", help="S1 à S5, DOSSIER : échoue s'il reste des marqueurs")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--racine", help="dépôt à analyser (défaut : celui qui contient ce script)")
    a = ap.parse_args()
    global RACINE
    if a.racine:
        RACINE = os.path.abspath(a.racine)

    if a.init:
        out = {}
        for cle, chemin in LIVRABLES.items():
            out[cle] = compter(open(os.path.join(RACINE, chemin), encoding="utf-8").read())[0]
        json.dump(out, open(GABARITS, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("gabarits enregistrés :", out)
        return 0

    lignes, avance = analyser()
    fautes = interdits(fichiers_suivis())
    if a.json:
        print(json.dumps({"livrables": lignes, "avancement": avance, "interdits": fautes}, ensure_ascii=False))
    else:
        rap = ["# Avancement du dépôt", "", "| Livrable | Marqueurs restants | Complétion | Critères cochés |", "|---|---|---|---|"]
        for cle, v in lignes.items():
            if not v["present"]:
                rap.append(f"| {v['fichier']} | fichier absent | | |")
                continue
            comp = f"{v['completion_pct']} %" if v["completion_pct"] is not None else "n/a"
            crit = f"{v['criteres_coches']}/{v['criteres_total']}" if v["criteres_total"] else "-"
            rap.append(f"| {v['fichier']} | {v['marqueurs_restants']} | {comp} | {crit} |")
        if avance:
            rap += ["", f"Stories : {avance['Fait']} faites, {avance['En cours']} en cours, {avance['Bloqué']} bloquées, "
                        f"{avance['À faire']} à faire, sur {avance['total']}."]
        rap += ["", "Fichiers interdits : " + ("aucun" if not fautes else "")]
        rap += [f"- {f} : {raison}" for f, raison in fautes]
        texte = "\n".join(rap)
        print(texte)
        resume = os.environ.get("GITHUB_STEP_SUMMARY")
        if resume:
            with open(resume, "a", encoding="utf-8") as fh:
                fh.write(texte + "\n")
    code = 1 if fautes else 0
    if a.strict:
        v = lignes.get(a.strict.upper())
        if not v or not v["present"]:
            print(f"livrable {a.strict} introuvable", file=sys.stderr)
            return 2
        if v["marqueurs_restants"]:
            print(f"--strict {a.strict} : {v['marqueurs_restants']} marqueur(s) restant(s)", file=sys.stderr)
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
