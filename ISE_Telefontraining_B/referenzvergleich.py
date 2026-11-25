"""Drei Live-Durchgänge mit neutralen Beleg-IDs; Aufruf: python referenzvergleich.py ZIELORDNER."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path

from evaluation_v03 import InvalidEvaluation, evaluate, load_knowledge
from training import Blablador, Modellfehler

REFERENCES = Path(__file__).parent / "beispiele" / "referenz"


def run(path, number, target):
    case = json.loads(path.read_text(encoding="utf-8"))
    expected = case.pop("expected")
    rubric, _ = load_knowledge(scenario_id=case["scenario_id"])
    originals = {}
    for index, message in enumerate(case["messages"], 1):
        neutral = f"m{index:03d}"
        originals[neutral] = message["id"]
        message["id"] = neutral
    service = {m["id"]: m["text"] for m in case["messages"] if m["role"] == "trainee"}
    model = Blablador(os.environ["BLABLADOR_API_KEY"], timeout=90)
    result = {"run": number, "model": model.modellname, "errors": [], "id_map": originals}
    for _ in range(3):
        try:
            report = evaluate({"snapshot": case, "rubric": rubric}, model)
        except (InvalidEvaluation, Modellfehler) as exc:
            result["errors"].append(str(exc))
            continue
        for row in report["criteria"] + report["strengths"] + report["improvements"]:
            for proof in row["evidence"]:
                assert proof["quote"] == service[proof["message_id"]]
        actual = [(f["rule_id"], originals[e["message_id"]], e["quote"])
                  for f in report["critical_findings"] for e in f["evidence"]]
        result["critical_match"] = actual == [(f["rule_id"], f["message_id"], f["quote"])
                                              for f in expected["critical_findings"]]
        result["feedback"] = report
        break
    (target / f"{path.stem}-{number}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path.stem, number, "OK" if "feedback" in result else "FEHLER", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    target = parser.parse_args().target
    target.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = [pool.submit(run, path, number, target)
                 for number in range(1, 4) for path in sorted(REFERENCES.glob("*.json"))]
        for task in tasks:
            task.result()
