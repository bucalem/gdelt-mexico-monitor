"""
fetch_gdelt.py
--------------
Descarga los archivos GKG mas recientes de GDELT 2.0 (publicos, sin API key).
Pensado para correr cada 15-30 min vía cron / GitHub Actions: por default solo
trae la ultima hora (4 archivos) con redundancia suficiente para no perder
ventanas si una corrida del workflow se retrasa o falla una vez.

Uso:
    python3 fetch_gdelt.py                  # ultima 1 hora (default)
    python3 fetch_gdelt.py --hours 4         # backfill manual de 4 horas
    python3 fetch_gdelt.py --out raw.tsv
"""
import argparse
import io
import sys
import time
import zipfile
import datetime
import urllib.request

BASE = "http://data.gdeltproject.org/gdeltv2/{ts}.gkg.csv.zip"
LASTUPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"


def get_latest_ts() -> str:
    req = urllib.request.urlopen(LASTUPDATE_URL, timeout=20)
    for line in req.read().decode().splitlines():
        if ".gkg.csv.zip" in line:
            fname = line.split()[-1].split("/")[-1]
            return fname.replace(".gkg.csv.zip", "")
    raise RuntimeError("No se encontro timestamp GKG en lastupdate.txt")


def download_one(ts: str):
    url = BASE.format(ts=ts)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = resp.read()
        zf = zipfile.ZipFile(io.BytesIO(data))
        name = zf.namelist()[0]
        return zf.read(name).decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [!] fallo {ts}: {e}", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=1.0, help="Horas hacia atras a descargar (default: 1)")
    ap.add_argument("--out", default="raw_gkg_latest.tsv", help="Archivo de salida (TSV crudo)")
    args = ap.parse_args()

    n_files = max(1, round(args.hours * 4))  # 4 archivos por hora (15 min c/u)

    latest = get_latest_ts()
    dt = datetime.datetime.strptime(latest, "%Y%m%d%H%M%S")

    total_lines = 0
    with open(args.out, "w", encoding="utf-8") as out:
        for i in range(n_files):
            ts = (dt - datetime.timedelta(minutes=15 * i)).strftime("%Y%m%d%H%M%S")
            print(f"Descargando {ts} ...")
            content = download_one(ts)
            if content:
                out.write(content)
                total_lines += content.count("\n")
            time.sleep(0.2)

    print(f"Listo. {total_lines} filas guardadas en {args.out}")


if __name__ == "__main__":
    main()
