"""
analyze_mexico.py
------------------
Filtra el GKG de GDELT 2.0 por menciones geograficas de Mexico, calcula tono
promedio (V2Tone) por bloque de 15 min y MANTIENE un historico acumulado en
data/mexico_tone_timeline.json, fusionando cada corrida con la anterior
(sin duplicar slots ya guardados) y recortando a una ventana movil.

Pensado para correr despues de fetch_gdelt.py en cada ejecucion del workflow.

Uso:
    python3 analyze_mexico.py --in raw_gkg_latest.tsv --out ../data/mexico_tone_timeline.json
"""
import argparse
import json
import re
import datetime
from collections import defaultdict

MX_LOC_RE = re.compile(r"#MX#")
ROLLING_DAYS = 3  # cuanta historia conservar en el timeline (recorte de tamano del JSON)


def parse_tone(tone_field):
    try:
        parts = tone_field.split(",")
        return {
            "avg_tone": float(parts[0]),
            "positive": float(parts[1]),
            "negative": float(parts[2]),
            "polarity": float(parts[3]),
        }
    except Exception:
        return None


def analyze_batch(path):
    """Procesa el TSV recien descargado y regresa agregados de ESTA corrida."""
    by_slot = defaultdict(list)     # "YYYY-MM-DDTHH:MM" -> [avg_tone,...]
    by_source = defaultdict(list)
    by_theme = defaultdict(int)
    rows_mx = 0
    rows_total = 0

    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            rows_total += 1
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 16:
                continue
            date_field, source, themes_v2, locs_v2, tone_field = (
                cols[1], cols[3], cols[8], cols[9], cols[15]
            )
            if not MX_LOC_RE.search(locs_v2):
                continue
            tone = parse_tone(tone_field)
            if not tone:
                continue
            try:
                dt = datetime.datetime.strptime(date_field, "%Y%m%d%H%M%S")
            except ValueError:
                continue
            rows_mx += 1
            slot = dt.strftime("%Y-%m-%dT%H:%M")
            by_slot[slot].append(tone["avg_tone"])
            by_source[source].append(tone["avg_tone"])
            for theme in themes_v2.split(";"):
                t = theme.split(",")[0].strip()
                if t:
                    by_theme[t] += 1

    return {
        "rows_total": rows_total,
        "rows_mx": rows_mx,
        "by_slot": by_slot,
        "by_source": by_source,
        "by_theme": by_theme,
    }


def load_existing(out_path):
    try:
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)
        # reindexar timeline existente por slot para poder fusionar
        slots = {row["time"]: row for row in existing.get("timeline", [])}
        return slots
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", default="raw_gkg_latest.tsv")
    ap.add_argument("--out", dest="outfile", default="../data/mexico_tone_timeline.json")
    args = ap.parse_args()

    batch = analyze_batch(args.infile)
    existing_slots = load_existing(args.outfile)

    # fusionar: los slots nuevos sobreescriben/agregan; los viejos se conservan
    for slot, vals in batch["by_slot"].items():
        existing_slots[slot] = {
            "time": slot,
            "avg_tone": round(sum(vals) / len(vals), 3),
            "n_articles": len(vals),
        }

    # recortar a la ventana movil (ROLLING_DAYS)
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=ROLLING_DAYS)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M")
    timeline = sorted(
        (row for slot, row in existing_slots.items() if slot >= cutoff_str),
        key=lambda r: r["time"],
    )

    # top fuentes / temas: de la corrida mas reciente (vista de "ahora mismo")
    top_sources = sorted(
        ({"source": s, "n": len(v), "avg_tone": round(sum(v) / len(v), 3)}
         for s, v in batch["by_source"].items()),
        key=lambda x: -x["n"],
    )[:15]
    top_themes = sorted(batch["by_theme"].items(), key=lambda x: -x[1])[:15]
    top_themes = [{"theme": t, "n": n} for t, n in top_themes]

    recent_vals = [v for row in timeline[-16:] for v in [row["avg_tone"]] * row["n_articles"]]
    overall_avg = round(sum(recent_vals) / len(recent_vals), 3) if recent_vals else None

    out = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "rows_total_scanned_last_run": batch["rows_total"],
        "rows_mexico_last_run": batch["rows_mx"],
        "overall_avg_tone_4h": overall_avg,
        "timeline": timeline,
        "top_sources": top_sources,
        "top_themes": top_themes,
    }

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Corrida: {batch['rows_total']} filas escaneadas | {batch['rows_mx']} menciones MX")
    print(f"Timeline acumulado: {len(timeline)} slots (ventana de {ROLLING_DAYS} dias)")
    print(f"Guardado en {args.outfile}")


if __name__ == "__main__":
    main()
