import argparse
import json
import re
from datetime import date
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data-source", required=True)
    parser.add_argument("-c", "--configuration", required=True)
    parser.add_argument("-v", "--variable", action="append", default=[])
    parser.add_argument("--results", type=Path, help="Conserver le JSON du scan à ce chemin")
    parser.add_argument("checks", nargs="+")
    args = parser.parse_args()

    if args.data_source == "bronze":
        variables = dict(item.split("=", 1) for item in args.variable if "=" in item)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", variables.get("BATCH_ID", "")):
            parser.error("Bronze exige BATCH_ID (lettres, chiffres, tirets ou soulignements).")
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", variables.get("REFERENCE_DATE", "")):
            parser.error("Bronze exige REFERENCE_DATE au format AAAA-MM-JJ.")
        try:
            date.fromisoformat(variables.get("REFERENCE_DATE", ""))
        except ValueError:
            parser.error("Bronze exige REFERENCE_DATE au format AAAA-MM-JJ.")

    command = ["soda", "scan", "-d", args.data_source, "-c", args.configuration]
    for variable in args.variable:
        command.extend(["-v", variable])

    with tempfile.TemporaryDirectory() as temporary_directory:
        results_file = Path(temporary_directory) / "scan-results.json"
        command.extend(["-srf", str(results_file), *args.checks])
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)

        if not results_file.is_file():
            print("Soda scan did not produce its results JSON.", file=sys.stderr)
            return result.returncode or 1

        scan_results = json.loads(results_file.read_text(encoding="utf-8"))
        if args.results:
            args.results.parent.mkdir(parents=True, exist_ok=True)
            args.results.write_text(json.dumps(scan_results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if scan_results["hasErrors"] or scan_results["hasFailures"]:
            return result.returncode or 2

        return 0


if __name__ == "__main__":
    raise SystemExit(main())
