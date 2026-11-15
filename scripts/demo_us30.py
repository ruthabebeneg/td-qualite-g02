"""Démonstration US-30 synthétique, indépendante de la base et du certificat."""
import argparse
import json
import sqlite3
from pathlib import Path


def demonstrer():
    with sqlite3.connect(":memory:") as connexion:
        connexion.execute("CREATE TABLE contrat (id TEXT, date_debut TEXT, date_fin TEXT)")
        connexion.executemany("INSERT INTO contrat VALUES (?, ?, ?)", [
            ("DEMO-1", "2026-01-01", "2026-12-31"),
            ("DEMO-2", "2026-05-01", "2026-04-01"),
            ("DEMO-3", "2026-01-01", None),
            ("DEMO-4", "2026-01-01", "2026-12-31"),
        ])
        def mesurer(etape):
            total, echecs = connexion.execute("""
                SELECT COUNT(*), SUM(date_debut IS NULL OR date_fin IS NULL
                                    OR date_fin <= date_debut) FROM contrat
            """).fetchone()
            return {"etape": etape, "regle": "RQ-001", "testees": total,
                    "echecs": echecs, "conformite_pct": 100 * (total - echecs) / total}
        mesures = [mesurer("initial"), mesurer("relance_sans_changement")]
        # Correction volontaire de la fixture ; aucune donnée du lot réel n'est utilisée.
        connexion.execute("UPDATE contrat SET date_fin = '2026-12-31' WHERE id IN ('DEMO-2', 'DEMO-3')")
        mesures.append(mesurer("apres_correction_fixture"))
    assert mesures[0]["conformite_pct"] == mesures[1]["conformite_pct"] == 50
    assert mesures[2]["conformite_pct"] == 100
    return {"nature": "démonstration pédagogique synthétique exécutée ; pas un historique de production",
            "source": "4 contrats fictifs en SQLite mémoire ; prédicat RQ-001",
            "effet_sur_certificat": "aucun", "mesures": mesures}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--svg", type=Path, help="Tracer les mesures calculées, distinctes du lot réel")
    args = parser.parse_args()
    resultat = demonstrer()
    contenu = json.dumps(resultat, ensure_ascii=False, indent=2) + "\n"
    if args.svg:
        points = [(100 + 210 * i, 220 - 1.5 * m["conformite_pct"]) for i, m in enumerate(resultat["mesures"])]
        polyline = " ".join(f"{x},{y}" for x, y in points)
        labels = ["Initial", "Sans changement", "Fixture corrigée"]
        marques = "".join(
            f'<circle cx="{x}" cy="{y}" r="6" fill="#145e83"/>'
            f'<text x="{x}" y="{y - 15}" text-anchor="middle">{m["conformite_pct"]:g} %</text>'
            f'<text x="{x}" y="260" text-anchor="middle">{label}</text>'
            for (x, y), m, label in zip(points, resultat["mesures"], labels)
        )
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="310" viewBox="0 0 640 310">
<rect width="640" height="310" fill="white"/>
<g font-family="sans-serif" font-size="16" fill="#173244">
<text x="320" y="28" text-anchor="middle">US-30 — RQ-001 : démonstration synthétique</text>
<path d="M60 60V220H580" fill="none" stroke="#8a9ca8"/>
<polyline points="{polyline}" fill="none" stroke="#145e83" stroke-width="3"/>{marques}
<text x="320" y="295" text-anchor="middle" font-size="13">4 contrats fictifs · SQL exécuté · aucun effet sur le certificat</text>
</g></svg>\n'''
        args.svg.parent.mkdir(parents=True, exist_ok=True)
        args.svg.write_text(svg, encoding="utf-8")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(contenu, encoding="utf-8")
    print(contenu, end="")
