#!/usr/bin/env python3
"""Base de pruebas para elegir entre anydoc y markitdown al convertir documentos a Markdown.

    db.py recomendar [--tipo T] ARCHIVO...   qué herramienta usar, con la evidencia y el comando
    db.py detectar [--tipo T] ARCHIVO...     formato, tipo de contenido y metadatos (JSON)
    db.py probar [--rep N] [--salida DIR] [--lote L] [--origen O] [--tipo T] ARCHIVO...
                                             mide las dos herramientas in-process y agrega filas
    db.py calificar ID CALIDAD [NOTA]        carga la calidad (0-5) de una fila
    db.py stats [--formato F] [--tipo T]     resumen por formato, tipo y herramienta, y duelos
    db.py limpiar-pies [--paginas N] [--aplicar] ARCHIVO.md
                                             quita pies de página repetidos (deja el primero)

Sólo biblioteca estándar. La base es datos/pruebas.csv y se toca únicamente desde acá.
"""

import argparse
import csv
import json
import math
import platform
import re
import shlex
import statistics
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DB = RAIZ / "datos" / "pruebas.csv"
NODE_DIR = Path.home() / ".local" / "share" / "convertir-documentos"

COLUMNAS = [
    "id", "fecha", "lote", "equipo", "archivo", "origen", "formato", "tipo", "paginas",
    "imagenes", "bytes_entrada", "generador", "herramienta", "version", "modo",
    "repeticiones", "ms", "salida_chars", "estado", "calidad", "notas",
]
HERRAMIENTAS = ("anydoc", "markitdown")
TIPOS = ("texto", "diapositivas", "escaneado", "ecuaciones", "tablas", "hoja-calculo", "libro", "correo", "otro")

FAMILIAS = {
    "texto-procesador": {"doc", "docx", "docm", "odt", "rtf"},
    "presentacion": {"ppt", "pps", "pot", "pptx", "pptm", "ppsx", "ppsm", "odp"},
    "hoja": {"xls", "xlsx", "xlsm", "xlsb", "ods"},
    "pdf": {"pdf"},
    "libro": {"epub"},
    "correo": {"msg"},
}
FAMILIA = {ext: fam for fam, exts in FAMILIAS.items() for ext in exts}

# Según el código de cada repo (anydoc 0.2.4, markitdown 0.1.8b1): extensiones que aceptan.
SOPORTE = {
    "anydoc": set(FAMILIA) - {"msg"},
    "markitdown": {"pdf", "docx", "pptx", "xlsx", "xls", "epub", "msg"},
}

# Cuando no hay calificaciones propias para el caso. Por defecto anydoc, que gana todos los
# formatos de oficina en el benchmark que publica (sin verificar); PDF de diapositivas, por lo
# observado con el material de la UNLP.
PREVIA = {("pdf", "diapositivas"): "markitdown"}


def soportan(formato):
    return [h for h in HERRAMIENTAS if formato in SOPORTE[h]]


def leer():
    if not DB.exists():
        return []
    with DB.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def escribir(filas):
    DB.parent.mkdir(parents=True, exist_ok=True)
    tmp = DB.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)
    tmp.replace(DB)


def salida_de(cmd, timeout=120):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def media(xs):
    return sum(xs) / len(xs)


def abreviar(ruta):
    try:
        return "~/" + str(ruta.relative_to(Path.home()))
    except ValueError:
        return str(ruta)


def equipo():
    cpu = ""
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            cpu = next((l.split(":", 1)[1].strip() for l in f if l.startswith("model name")), "")
    except OSError:
        pass
    cpu = re.sub(r"\s+with .*$", "", cpu) or platform.machine()
    try:
        so = platform.freedesktop_os_release().get("NAME", "")
    except OSError:
        so = ""
    return f"{cpu} / {so or platform.system()}"


def detectar(ruta, tipo=None):
    ext = ruta.suffix.lower().lstrip(".")
    fam = FAMILIA.get(ext, "")
    d = {"archivo": str(ruta), "formato": ext, "familia": fam, "tipo": "otro", "paginas": "",
         "imagenes": "", "bytes_entrada": ruta.stat().st_size, "generador": ""}
    ecuaciones = False

    if fam == "pdf":
        info = {}
        for linea in salida_de(["pdfinfo", str(ruta)]).splitlines():
            clave, _, valor = linea.partition(":")
            info[clave.strip()] = valor.strip()
        d["generador"] = info.get("Creator") or info.get("Producer", "")
        paginas = int(info["Pages"]) if info.get("Pages", "").isdigit() else 0
        d["paginas"] = paginas or ""
        if info:
            d["imagenes"] = len(salida_de(["pdfimages", "-list", str(ruta)]).splitlines()[2:])
        chars = len(re.sub(r"\s", "", salida_de(["pdftotext", "-q", str(ruta), "-"], 300)))
        tam = re.search(r"([\d.]+) x ([\d.]+)", info.get("Page size", ""))
        if paginas and chars / paginas < 30:
            d["tipo"] = "escaneado"
        elif tam and float(tam[1]) > float(tam[2]):
            d["tipo"] = "diapositivas"
        else:
            d["tipo"] = "texto"
    elif zipfile.is_zipfile(ruta) and fam:
        with zipfile.ZipFile(ruta) as z:
            nombres = z.namelist()
            d["imagenes"] = sum(1 for n in nombres if re.search(r"(^|/)(media|Pictures|images?)/.", n))
            if "docProps/app.xml" in nombres:
                app = re.search(rb"<Application>([^<]*)</Application>", z.read("docProps/app.xml"))
                d["generador"] = app[1].decode(errors="replace") if app else ""
            partes = [n for n in nombres if re.fullmatch(r"word/document\.xml|ppt/slides/slide\d+\.xml", n)]
            ecuaciones = any(b"<m:oMath" in z.read(n) for n in partes)

    if fam and fam != "pdf":
        d["tipo"] = {
            "presentacion": "diapositivas", "hoja": "hoja-calculo", "libro": "libro", "correo": "correo",
            "texto-procesador": "ecuaciones" if ecuaciones else "texto",
        }[fam]
    if tipo:
        d["tipo"] = tipo
    return d


def pares_velocidad(filas):
    """Cociente ms markitdown / ms anydoc de cada archivo medido in-process con las dos en el mismo lote."""
    grupos = defaultdict(dict)
    for f in filas:
        if f["modo"] == "inproc" and f["estado"] == "ok" and f["ms"]:
            grupos[(f["lote"], f["archivo"])][f["herramienta"]] = float(f["ms"])
    return [g["markitdown"] / g["anydoc"] for g in grupos.values() if len(g) == 2 and g["anydoc"] > 0]


def recomendar(d, filas):
    fmt, fam, tipo = d["formato"], d["familia"], d["tipo"]
    if not fam:
        return None, "fuera de alcance: no es un documento (Word, PowerPoint, Excel, PDF, EPUB, .msg)", []
    candidatas = soportan(fmt)
    if len(candidatas) == 1:
        return candidatas[0], f"solo {candidatas[0]} soporta .{fmt}", []

    comunes = {x for x in FAMILIAS[fam] if all(x in SOPORTE[h] for h in HERRAMIENTAS)}
    niveles = [
        (f"{fmt}+{tipo}", lambda f: f["formato"] == fmt and f["tipo"] == tipo),
        (f"familia {fam}+{tipo}", lambda f: f["formato"] in comunes and f["tipo"] == tipo),
    ]
    # En PDF el tipo pesa demasiado (diapositivas y texto dan resultados opuestos) para ignorarlo.
    if fam != "pdf" and tipo != "escaneado":
        niveles.append((f"{fmt} de cualquier tipo", lambda f: f["formato"] == fmt))

    for nombre, cond in niveles:
        sub = [f for f in filas if cond(f)]
        cal = {h: [int(f["calidad"]) for f in sub if f["herramienta"] == h and f["calidad"] != ""]
               for h in HERRAMIENTAS}
        if not all(cal.values()):
            continue
        ratios = pares_velocidad(sub)
        prom = {h: media(cal[h]) for h in HERRAMIENTAS}
        if abs(prom["anydoc"] - prom["markitdown"]) >= 0.5:
            elegida = max(prom, key=prom.get)
        else:
            elegida = "markitdown" if ratios and statistics.median(ratios) < 1 else "anydoc"
        n = min(len(v) for v in cal.values())
        confianza = "alta" if n >= 5 else "media" if n >= 2 else "baja"
        evidencia = [f"calidad {h} {prom[h]:.1f} (n={len(cal[h])})" for h in HERRAMIENTAS]
        if ratios:
            evidencia.append(f"markitdown tarda {statistics.median(ratios):.1f}x lo de anydoc "
                             f"(mediana de {len(ratios)} pares in-process)")
        return elegida, f"nivel {nombre}, confianza {confianza}", evidencia

    elegida = PREVIA.get((fmt, tipo), "anydoc")
    return elegida, "sin calificaciones propias, regla previa", []


def comando(herramienta, archivo):
    destino = archivo.with_suffix(".md")
    if herramienta == "anydoc":
        cmd = ["pnpm", "dlx", "@firecrawl/anydoc", str(archivo), "-o", str(destino)]
    else:
        cmd = ["uvx", "--from", "markitdown[all]", "markitdown", str(archivo), "-o", str(destino)]
    return shlex.join(cmd)


def cmd_recomendar(a):
    filas = leer()
    for archivo in a.archivos:
        ruta = Path(archivo).expanduser().resolve()
        if not ruta.is_file():
            print(f"{archivo}: no existe\n")
            continue
        d = detectar(ruta, a.tipo)
        herramienta, motivo, evidencia = recomendar(d, filas)
        meta = ", ".join(x for x in (
            f"{d['paginas']} págs" if d["paginas"] else "",
            f"{d['imagenes']} imágenes" if d["imagenes"] != "" else "",
            d["generador"],
        ) if x)
        print(ruta)
        print(f"  .{d['formato']} · tipo {d['tipo']}" + (f" ({meta})" if meta else ""))
        if not herramienta:
            print(f"  {motivo}\n")
            continue
        print(f"  usar: {herramienta} [{motivo}]")
        for e in evidencia:
            print(f"  evidencia: {e}")
        print(f"  comando: {comando(herramienta, ruta)}")
        if d["tipo"] == "escaneado":
            print("  ojo: parece escaneado. Ninguna hace OCR local: anydoc falla con NeedsOcr y markitdown devuelve vacío.")
        if herramienta == "markitdown" and d["familia"] == "pdf" and d["tipo"] == "diapositivas":
            print(f"  después: db.py limpiar-pies --paginas {d['paginas'] or 0} {shlex.quote(str(ruta.with_suffix('.md')))}")
        if "confianza alta" not in motivo and len(soportan(d["formato"])) == 2:
            print(f"  para sumar evidencia: db.py probar {shlex.quote(str(ruta))}")
        print()


def cmd_detectar(a):
    for archivo in a.archivos:
        print(json.dumps(detectar(Path(archivo).expanduser().resolve(), a.tipo), ensure_ascii=False))


def correr_medidor(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    resultados = {}
    for linea in proc.stdout.splitlines():
        if linea.startswith("{"):
            r = json.loads(linea)
            resultados[r["indice"]] = r
    if proc.returncode != 0 and not resultados:
        sys.exit(f"falló {shlex.join(cmd[:3])}: {proc.stderr.strip()[-800:]}")
    return resultados


def cmd_probar(a):
    if a.rep < 1:
        sys.exit("--rep tiene que ser 1 o más")
    rutas = [Path(x).expanduser().resolve() for x in a.archivos]
    faltan = [str(r) for r in rutas if not r.is_file()]
    if faltan:
        sys.exit("no existen: " + ", ".join(faltan))
    salida = Path(a.salida).expanduser().resolve() if a.salida else Path(tempfile.mkdtemp(prefix="convertir-documentos-"))
    salida.mkdir(parents=True, exist_ok=True)
    if not (NODE_DIR / "node_modules" / "@firecrawl" / "anydoc").is_dir():
        NODE_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(["pnpm", "add", "@firecrawl/anydoc", "--dir", str(NODE_DIR)], check=True)

    argumentos = [str(a.rep), str(salida), *map(str, rutas)]
    medidos = {
        "anydoc": correr_medidor(["node", str(RAIZ / "medir_anydoc.mjs"), *argumentos]),
        "markitdown": correr_medidor(["uvx", "--from", "markitdown[all]", "python",
                                      str(RAIZ / "medir_markitdown.py"), *argumentos]),
    }

    filas = leer()
    siguiente = max((int(f["id"]) for f in filas), default=0) + 1
    hoy = date.today().isoformat()
    lote = a.lote or f"{hoy}-probar"
    eq = equipo()
    print(f"salidas en {salida}")
    for i, ruta in enumerate(rutas, 1):
        d = detectar(ruta, a.tipo)
        for h in HERRAMIENTAS:
            r = medidos[h].get(i)
            if r is None:
                print(f"  {h}: sin resultado para {ruta.name}")
                continue
            filas.append({
                "id": siguiente, "fecha": hoy, "lote": lote, "equipo": eq, "archivo": abreviar(ruta),
                "origen": a.origen, "formato": d["formato"], "tipo": d["tipo"], "paginas": d["paginas"],
                "imagenes": d["imagenes"], "bytes_entrada": d["bytes_entrada"], "generador": d["generador"],
                "herramienta": h, "version": r.get("version", ""), "modo": "inproc", "repeticiones": a.rep,
                "ms": r.get("ms", ""), "salida_chars": r.get("chars", 0), "estado": r["estado"],
                "calidad": "", "notas": re.sub(r"\s+", " ", r.get("error", "")).strip(),
            })
            print(f"  #{siguiente} {h:<10} {r['estado']:<12} {r.get('ms', '')} ms  "
                  f"{r.get('chars', 0)} chars  {r.get('salida', '')}")
            siguiente += 1
    escribir(filas)
    print("\nRevisá las salidas y calificá cada fila: db.py calificar ID 0-5 'nota'")


def cmd_calificar(a):
    if not 0 <= a.calidad <= 5:
        sys.exit("la calidad va de 0 a 5")
    filas = leer()
    fila = next((f for f in filas if f["id"] == str(a.id)), None)
    if fila is None:
        sys.exit(f"no hay fila {a.id}")
    fila["calidad"] = str(a.calidad)
    if a.nota:
        fila["notas"] = f"{fila['notas']} | {a.nota}" if fila["notas"] else a.nota
    escribir(filas)
    print(f"#{a.id} {fila['herramienta']} {Path(fila['archivo']).name}: calidad {a.calidad}")


def imprimir(encabezado, tabla):
    anchos = [max(len(str(x)) for x in col) for col in zip(encabezado, *tabla)]
    for fila in (encabezado, *tabla):
        print("  ".join(str(x).ljust(w) for x, w in zip(fila, anchos)).rstrip())


def cmd_stats(a):
    filas = [f for f in leer()
             if (not a.formato or f["formato"] == a.formato) and (not a.tipo or f["tipo"] == a.tipo)]
    if not filas:
        print("sin filas")
        return

    grupos = defaultdict(list)
    for f in filas:
        grupos[(f["formato"], f["tipo"], f["herramienta"])].append(f)
    tabla = []
    for (fmt, tipo, h), fs in sorted(grupos.items()):
        cal = [int(f["calidad"]) for f in fs if f["calidad"] != ""]
        ms = {m: [float(f["ms"]) for f in fs if f["modo"] == m and f["estado"] == "ok" and f["ms"]]
              for m in ("inproc", "cli")}
        tabla.append((
            fmt, tipo, h, f"{sum(f['estado'] == 'ok' for f in fs)}/{len(fs)}",
            f"{media(cal):.1f} (n={len(cal)})" if cal else "-",
            f"{statistics.median(ms['inproc']):.1f}" if ms["inproc"] else "-",
            f"{statistics.median(ms['cli']):.0f}" if ms["cli"] else "-",
        ))
    print("Por formato, tipo y herramienta (ms = mediana; cli incluye el arranque de pnpm/uvx):")
    imprimir(("formato", "tipo", "herramienta", "ok", "calidad", "ms inproc", "ms cli"), tabla)

    pares = defaultdict(dict)
    for f in filas:
        pares[(f["lote"], f["archivo"])][f["herramienta"]] = f
    duelos, velocidad = defaultdict(Counter), defaultdict(list)
    for par in pares.values():
        if len(par) != 2:
            continue
        ad, mid = par["anydoc"], par["markitdown"]
        clave = (ad["formato"], ad["tipo"])
        if ad["calidad"] != "" and mid["calidad"] != "":
            c_ad, c_mid = int(ad["calidad"]), int(mid["calidad"])
            duelos[clave]["anydoc" if c_ad > c_mid else "markitdown" if c_mid > c_ad else "empate"] += 1
        if ad["modo"] == "inproc" == mid["modo"] and ad["estado"] == "ok" == mid["estado"] and float(ad["ms"]) > 0:
            velocidad[clave].append(float(mid["ms"]) / float(ad["ms"]))
    tabla = []
    for clave in sorted(set(duelos) | set(velocidad)):
        c, v = duelos[clave], velocidad[clave]
        tabla.append((*clave, c["anydoc"], c["markitdown"], c["empate"],
                      f"{statistics.median(v):.1f}x (n={len(v)})" if v else "-"))
    print("\nDuelos por archivo (mismo lote; velocidad = ms markitdown / ms anydoc, in-process):")
    imprimir(("formato", "tipo", "gana anydoc", "gana markitdown", "empate", "velocidad"), tabla)


def cmd_limpiar(a):
    ruta = Path(a.archivo).expanduser()
    lineas = ruta.read_text(encoding="utf-8").split("\n")

    def norm(s):
        return re.sub(r"\s+", " ", s).strip()

    cuenta = Counter(n for n in map(norm, lineas) if len(n) >= 30 and not n.startswith("|"))
    umbral = max(3, math.ceil(a.paginas / 2)) if a.paginas else 5
    pies = {n: c for n, c in cuenta.items() if c >= umbral}
    if not pies:
        print(f"sin pies repetidos (umbral: {umbral} apariciones de una línea de 30+ caracteres)")
        return
    for n, c in sorted(pies.items(), key=lambda x: -x[1]):
        print(f"  {c}x  {n[:110]}")
    if not a.aplicar:
        print("\nsin --aplicar no se toca nada")
        return
    vistos, salida = set(), []
    for linea in lineas:
        n = norm(linea)
        if n in pies:
            if n in vistos:
                continue
            vistos.add(n)
        salida.append(linea)
    ruta.write_text(re.sub(r"\n{3,}", "\n\n", "\n".join(salida)), encoding="utf-8")
    print(f"\nquitadas {len(lineas) - len(salida)} líneas; queda la primera aparición de cada pie")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("recomendar")
    s.add_argument("--tipo", choices=TIPOS)
    s.add_argument("archivos", nargs="+")
    s.set_defaults(f=cmd_recomendar)

    s = sub.add_parser("detectar")
    s.add_argument("--tipo", choices=TIPOS)
    s.add_argument("archivos", nargs="+")
    s.set_defaults(f=cmd_detectar)

    s = sub.add_parser("probar")
    s.add_argument("--rep", type=int, default=3)
    s.add_argument("--salida")
    s.add_argument("--lote")
    s.add_argument("--origen", default="")
    s.add_argument("--tipo", choices=TIPOS)
    s.add_argument("archivos", nargs="+")
    s.set_defaults(f=cmd_probar)

    s = sub.add_parser("calificar")
    s.add_argument("id", type=int)
    s.add_argument("calidad", type=int)
    s.add_argument("nota", nargs="?", default="")
    s.set_defaults(f=cmd_calificar)

    s = sub.add_parser("stats")
    s.add_argument("--formato")
    s.add_argument("--tipo")
    s.set_defaults(f=cmd_stats)

    s = sub.add_parser("limpiar-pies")
    s.add_argument("--paginas", type=int, default=0)
    s.add_argument("--aplicar", action="store_true")
    s.add_argument("archivo")
    s.set_defaults(f=cmd_limpiar)

    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
