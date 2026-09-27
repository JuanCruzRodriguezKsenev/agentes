"""Mide markitdown in-process. Lo llama db.py:

    uvx --from 'markitdown[all]==0.1.5' python medir_markitdown.py REP SALIDA ARCHIVO...

Una línea JSON por archivo. La primera conversión de cada archivo es de calentamiento y no se cuenta.
"""

import json
import statistics
import sys
import time
from importlib.metadata import version
from pathlib import Path

from markitdown import MarkItDown

rep, salida, archivos = int(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
salida.mkdir(parents=True, exist_ok=True)
md = MarkItDown()

for i, archivo in enumerate(archivos, 1):
    r = {"indice": i, "herramienta": "markitdown", "version": version("markitdown")}
    tiempos, texto = [], ""
    for n in range(rep + 1):
        t = time.perf_counter()
        try:
            texto = md.convert_local(archivo).markdown or ""
        except Exception as e:  # noqa: BLE001 - se registra cualquier falla como resultado de la prueba
            tiempos.append((time.perf_counter() - t) * 1000)
            nombre = type(e).__name__
            r["estado"] = "no_soportado" if nombre == "UnsupportedFormatException" else "error"
            r["error"] = f"{nombre}: {e}"[:300]
            texto = ""
            break
        if n:
            tiempos.append((time.perf_counter() - t) * 1000)
    r["ms"] = round(statistics.median(tiempos), 1)
    r["chars"] = len(texto)
    if "estado" not in r:
        r["estado"] = "ok" if texto.strip() else "vacio"
        r["salida"] = str(salida / f"{i:02d}-{Path(archivo).stem}.markitdown.md")
        Path(r["salida"]).write_text(texto, encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False), flush=True)
