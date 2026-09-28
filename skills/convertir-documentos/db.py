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
    db.py verificar [--paginas A-B] [--imagenes DIR] ORIGINAL SALIDA.md
                                             chequeos automáticos (filtro previo) y render de TODAS las
                                             páginas del tramo para la revisión visual, en lotes
    db.py transcribir [--paginas A-B] ORIGINAL DIR
                                             renderiza las páginas para transcribirlas desde la imagen
    db.py ensamblar [--reemplazar] [--conversor C] ORIGINAL DIR SALIDA.md
                                             arma o actualiza el .md con DIR/pag-NNN.md, entre marcas de página
    db.py marcar SALIDA.md --revision INFORME.txt [--paginas A-B]
    db.py marcar SALIDA.md --pendiente
                                             verificación del agente en el frontmatter, con el md5 del cuerpo
    db.py estado [--paginas A-B] SALIDA.md   verificación vigente del agente y de Juan; sale con 0 sólo
                                             si la del agente está en ok y vigente para esas páginas
    db.py huella [--paginas A-B] SALIDA.md   md5 del cuerpo (o del tramo) que se anota en la wiki

Sólo biblioteca estándar. La base es datos/pruebas.csv y se toca únicamente desde acá.
"""

import argparse
import csv
import hashlib
import html
import json
import math
import platform
import re
import shlex
import statistics
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DB = RAIZ / "datos" / "pruebas.csv"
NODE_DIR = Path.home() / ".local" / "share" / "convertir-documentos"

# Fijada: desde 0.1.6 markitdown pega las palabras en PDF de Google Docs e inventa una tabla por
# línea en PDF de diapositivas (0.1.5 no; pdfminer no influye). Antes de subirla, medir con `probar`
# y revisar palabras pegadas. Informe en ~/Boveda/Sistema, 2026-09-26.
MARKITDOWN = "markitdown[all]==0.1.5"

COLUMNAS = [
    "id", "fecha", "lote", "equipo", "archivo", "origen", "formato", "tipo", "paginas",
    "imagenes", "bytes_entrada", "generador", "herramienta", "version", "modo",
    "repeticiones", "ms", "salida_chars", "estado", "calidad", "notas",
    "paginas_marcadas", "cobertura_min",
]
HERRAMIENTAS = ("anydoc", "markitdown")
TIPOS = ("texto", "codigo", "diapositivas", "escaneado", "ecuaciones", "tablas", "hoja-calculo", "libro", "correo", "otro")

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

# Fuentes de matemática de LaTeX (Computer Modern, AMS, Latin Modern) y afines. Detectan las páginas
# con fórmulas sin mirarlas: pdftotext saca los símbolos igual de mal que los conversores, así que
# contar símbolos no sirve. Probado con 3 apuntes de Matemática C y 8 PDFs sin fórmulas, 2026-09-27.
# Sin CMSY ni LASY: LaTeX las usa para las viñetas de cualquier lista, haya fórmulas o no.
FUENTES_MATE = re.compile(r"^(CM(MI|EX|MIB)\d+|MSBM\d+|MSAM\d+|BBOLD\d+|Mathematica\d"
                          r"|LMMath|LatinModernMath|STIX\w*Math|CambriaMath)")
# Verificación página por página (prototipos de bibliotecario, ~/Boveda/Sistema/adjuntos, 2026-09-26).
UMBRAL_COBERTURA = 0.9
# Páginas por subagente en la revisión visual y en la transcripción. Es el tamaño del lote, NO un
# tope de páginas miradas: un `ok` exige haber mirado todas las del tramo (Juan, 2026-09-28).
LOTE = 10
DPI_REVISION = 110   # a 70 ppp no se distinguen subíndices, ≤ de < ni ≠ de =
DPI_TRANSCRIBIR = 150
MARCA_PAGINA = re.compile(r"^<!-- pág (\d+) -->[ \t]*$", re.M)
TRANSCRIPCION = "transcripción desde la imagen"
SIMBOLOS_EXTRA = set("∈∉⊂⊆∪∩∀∃ⁿ₀₁₂₃ᵢⱼ")


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


def fuentes_mate(ruta, paginas):
    """De las páginas indicadas (1-based), las que usan fuentes de matemática."""
    def usa(*rango):
        salida = salida_de(["pdffonts", *rango, str(ruta)]).splitlines()[2:]
        return any(FUENTES_MATE.match(l.split()[0].partition("+")[2] or l.split()[0]) for l in salida if l.split())
    if not usa():
        return []
    return [i for i in paginas if usa("-f", str(i), "-l", str(i))]


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
        elif paginas and len(fuentes_mate(ruta, muestra := sorted({1 + k * paginas // 20 for k in range(20)}))) >= 0.3 * len(muestra):
            d["tipo"] = "ecuaciones"
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

    # En PDF sólo cuenta markitdown en la versión fijada: las calificaciones con 0.1.6+ miden la regresión.
    version = MARKITDOWN.partition("==")[2]
    filas = [f for f in filas if not (f["formato"] == "pdf" and f["herramienta"] == "markitdown"
                                       and f["version"] != version)]
    for nombre, cond in niveles:
        sub = [f for f in filas if cond(f)]
        cal = {h: [int(f["calidad"]) for f in sub if f["herramienta"] == h and f["calidad"] != ""]
               for h in HERRAMIENTAS}
        if not all(cal.values()):
            continue
        ratios = pares_velocidad(sub)
        prom = {h: media(cal[h]) for h in HERRAMIENTAS}
        n = min(len(v) for v in cal.values())
        if abs(prom["anydoc"] - prom["markitdown"]) >= 0.5:
            elegida = max(prom, key=prom.get)
            confianza = "confianza " + ("alta" if n >= 5 else "media" if n >= 2 else "baja")
        else:
            elegida = "markitdown" if ratios and statistics.median(ratios) < 1 else "anydoc"
            confianza = (f"calidad empatada ({prom['anydoc']:.1f} contra {prom['markitdown']:.1f}), "
                         "se elige por velocidad")
        evidencia = [f"calidad {h} {prom[h]:.1f} (n={len(cal[h])})" for h in HERRAMIENTAS]
        if ratios:
            evidencia.append(f"markitdown tarda {statistics.median(ratios):.1f}x lo de anydoc "
                             f"(mediana de {len(ratios)} pares in-process)")
        return elegida, f"nivel {nombre}, {confianza}", evidencia

    elegida = PREVIA.get((fmt, tipo), "anydoc")
    return elegida, "sin calificaciones propias, regla previa", []


def comando(herramienta, archivo):
    destino = archivo.with_suffix(".md")
    if herramienta == "anydoc":
        cmd = ["pnpm", "dlx", "@firecrawl/anydoc", str(archivo), "-o", str(destino)]
    else:
        cmd = ["uvx", "--from", MARKITDOWN, "markitdown", str(archivo), "-o", str(destino)]
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
        if d["familia"] == "pdf" and d["tipo"] == "ecuaciones":
            print("  ojo: matemática de LaTeX. Ninguna la convierte bien (anydoc cambia ∈ por 2 y ∀ por 8, markitdown "
                  "deja (cid:NN) e inventa tablas). Avisale al usuario antes de convertir.")
        if "empatada" in motivo and d["familia"] == "pdf":
            print("  ojo: empate. Convertí con las dos y corré db.py verificar sobre cada salida; quedate con la "
                  "que tenga menos páginas marcadas.")
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
        "markitdown": correr_medidor(["uvx", "--from", MARKITDOWN, "python",
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
                **resumen_verificacion(ruta, r),
            })
            print(f"  #{siguiente} {h:<10} {r['estado']:<12} {r.get('ms', '')} ms  "
                  f"{r.get('chars', 0)} chars  {r.get('salida', '')}")
            siguiente += 1
    escribir(filas)
    print("\nRevisá las salidas y calificá cada fila: db.py calificar ID 0-5 'nota'")


def resumen_verificacion(ruta, r):
    if r["estado"] != "ok" or not r.get("salida") or not Path(r["salida"]).is_file():
        return {}
    v = verificar(ruta, Path(r["salida"]))
    if not v:
        return {}
    return {"paginas_marcadas": f"{len(v['marcadas'])}/{v['paginas']}", "cobertura_min": f"{v['cobertura_min']:.2f}"}


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


def palabras(texto):
    return re.findall(r"[a-záéíóúüñ0-9]{3,}", unicodedata.normalize("NFC", texto).lower())


def simbolos(texto):
    return Counter(c for c in texto if unicodedata.category(c) in ("Sm", "So") or c in SIMBOLOS_EXTRA)


def norm_linea(linea):
    linea = re.sub(r"^\s*(?:[-*+>]\s+|#+\s+|\d+\.\s+)*", "", linea).replace("`", "")
    return re.sub(r"\s+", " ", re.sub(r"\\([\\`*_{}\[\]()#+\-.!|<>])", r"\1", linea)).strip()


def textos_por_pagina(ruta):
    """Texto de cada página del original: páginas de un PDF, diapositivas de un pptx, un solo bloque en docx."""
    ext = ruta.suffix.lower()
    if ext == ".pdf":
        paginas = salida_de(["pdftotext", "-q", "-layout", str(ruta), "-"], 600).split("\f")
        return paginas[:-1] if paginas and not paginas[-1].strip() else paginas
    if ext in (".pptx", ".docx") and zipfile.is_zipfile(ruta):
        with zipfile.ZipFile(ruta) as z:
            if ext == ".pptx":
                partes = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                                key=lambda n: int(re.search(r"\d+", n)[0]))
                return [html.unescape(" ".join(re.findall(r"<a:t>([^<]*)</a:t>", z.read(n).decode("utf-8", "replace"))))
                        for n in partes]
            xml = z.read("word/document.xml").decode("utf-8", "replace")
            return [html.unescape("\n".join("".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", p))
                              for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)))]
    return None


def verificar(original, salida):
    """Chequeos automáticos por página. None si el formato no se puede verificar así."""
    textos = textos_por_pagina(original)
    if textos is None:
        return None
    md = unicodedata.normalize("NFC", salida.read_text(encoding="utf-8"))
    md_palabras, md_simbolos = Counter(palabras(md)), simbolos(md)
    md_lineas = {norm_linea(l) for l in md.splitlines()}
    formulas = set(fuentes_mate(original, range(1, len(textos) + 1))) if original.suffix.lower() == ".pdf" else set()

    coberturas, marcadas = {}, {}
    for i, texto in enumerate(textos, 1):
        motivos = []
        ps = palabras(texto)
        if len(ps) >= 5:
            coberturas[i] = sum(1 for w in ps if md_palabras[w]) / len(ps)
            if coberturas[i] < UMBRAL_COBERTURA:
                motivos.append(f"cobertura {coberturas[i]:.2f}")
        faltan = sum((simbolos(unicodedata.normalize("NFC", texto)) - md_simbolos).values())
        if faltan > 2:
            motivos.append(f"{faltan} símbolos que no están en la salida")
        codigo = [norm_linea(l) for l in texto.splitlines() if re.search(r"[;{}]\s*$", l.strip()) and len(l.strip()) > 8]
        perdidas = [c for c in codigo if c not in md_lineas]
        if len(codigo) >= 3 and len(perdidas) / len(codigo) > 0.5:
            motivos.append(f"{len(perdidas)} de {len(codigo)} líneas de código no quedaron como línea")
        if motivos:
            marcadas[i] = motivos

    n = len(textos)
    pegadas = sum(1 for l in md.splitlines() if re.search(r"[a-záéíóúüñ]{35,}", l))
    return {
        "paginas": n, "marcadas": marcadas, "formulas": sorted(formulas), "pegadas": pegadas,
        "cobertura_min": min(coberturas.values(), default=1.0),
        "cobertura_media": media(list(coberturas.values())) if coberturas else 1.0,
        "peor": min(coberturas, key=coberturas.get) if coberturas else None,
    }


def rangos(nums):
    grupos, inicio = [], None
    for i, x in enumerate(nums):
        if inicio is None:
            inicio = x
        if i + 1 == len(nums) or nums[i + 1] != x + 1:
            grupos.append(str(inicio) if inicio == x else f"{inicio}-{x}")
            inicio = None
    return ", ".join(grupos)


def leer_rango(texto):
    """'1-24, 30' → [1..24, 30]."""
    paginas = set()
    for parte in re.split(r"[,\s]+", texto.strip()):
        if not parte:
            continue
        m = re.fullmatch(r"(\d+)(?:[-–](\d+))?", parte)
        if not m:
            sys.exit(f"rango inválido: {texto!r} (se escribe 1-24 o 3,7,19)")
        a, b = int(m[1]), int(m[2] or m[1])
        paginas.update(range(min(a, b), max(a, b) + 1))
    return sorted(paginas)


def renderizar(original, paginas, destino, dpi):
    destino.mkdir(parents=True, exist_ok=True)
    for i in paginas:
        subprocess.run(["pdftoppm", "-f", str(i), "-l", str(i), "-r", str(dpi), "-png", "-singlefile",
                        str(original), str(destino / f"pag-{i:03d}")], check=True)


def lotes(paginas):
    return [paginas[i:i + LOTE] for i in range(0, len(paginas), LOTE)]


def cmd_verificar(a):
    original, salida = Path(a.original).expanduser().resolve(), Path(a.salida).expanduser().resolve()
    for r in (original, salida):
        if not r.is_file():
            sys.exit(f"no existe: {r}")
    v = verificar(original, salida)
    if v is None:
        print(f"{original.suffix} no se verifica página por página (sólo PDF, pptx y docx): revisá la salida a mano.")
        return
    tramo = leer_rango(a.paginas) if a.paginas else list(range(1, v["paginas"] + 1))
    if tramo[-1] > v["paginas"]:
        sys.exit(f"el original tiene {v['paginas']} páginas y el tramo llega a {tramo[-1]}")
    unidad = "págs" if original.suffix.lower() == ".pdf" else "diapositivas" if original.suffix.lower() == ".pptx" else "bloque"
    print(f"{abreviar(original)} → {salida.name}" + (f" · tramo {rangos(tramo)}" if a.paginas else ""))
    peor = f", mínima {v['cobertura_min']:.2f} (pág {v['peor']})" if v["peor"] else ""
    print(f"  {v['paginas']} {unidad} · cobertura media {v['cobertura_media']:.2f}{peor}")
    if v["pegadas"] > 3:
        print(f"  PALABRAS PEGADAS: {v['pegadas']} líneas con una palabra de 35+ letras. La salida no sirve: convertí con la otra.")
    marcadas = {i: m for i, m in v["marcadas"].items() if i in tramo}
    if marcadas:
        print(f"  marcadas ({len(marcadas)} de {len(tramo)}):")
        for i, motivos in sorted(marcadas.items()):
            print(f"    pág {i}: " + "; ".join(motivos))
    else:
        print("  marcadas: ninguna")
    formulas = [i for i in v["formulas"] if i in tramo]
    if formulas:
        print(f"  fórmulas (fuentes de LaTeX) en {len(formulas)} págs: {rangos(formulas)}. "
              "Los chequeos automáticos no ven la matemática: sólo la revisión visual.")
    print("  Esto es un filtro previo: ninguna métrica alcanza para un ok. El ok sale de mirar TODAS las páginas del tramo.")
    if original.suffix.lower() != ".pdf":
        print("  revisión visual: sólo PDF. Exportá a PDF (soffice --headless --convert-to pdf) y verificá ese.")
        return
    grupos = lotes(tramo)
    print(f"  revisión visual: {len(tramo)} págs en {len(grupos)} lote(s) de hasta {LOTE}, un subagente por lote:")
    for g in grupos:
        print(f"    {rangos(g)}")
    if a.imagenes:
        destino = Path(a.imagenes).expanduser()
        renderizar(original, tramo, destino, a.dpi)
        print(f"  imágenes ({a.dpi} ppp): {abreviar(destino)}/pag-NNN.png")


def cmd_transcribir(a):
    original = Path(a.original).expanduser().resolve()
    if original.suffix.lower() != ".pdf" or not original.is_file():
        sys.exit(f"transcribir es para PDF: {original}")
    n = len(textos_por_pagina(original))
    tramo = leer_rango(a.paginas) if a.paginas else list(range(1, n + 1))
    if tramo[-1] > n:
        sys.exit(f"el original tiene {n} páginas y el tramo llega a {tramo[-1]}")
    destino = Path(a.dir).expanduser()
    renderizar(original, tramo, destino, a.dpi)
    print(f"{abreviar(original)}: {len(tramo)} págs renderizadas a {a.dpi} ppp en {abreviar(destino)}/pag-NNN.png")
    print(f"Un subagente por lote; cada uno escribe {abreviar(destino)}/pag-NNN.md por página:")
    for g in lotes(tramo):
        print(f"  {rangos(g)}")
    print(f"Después: db.py ensamblar {shlex.quote(str(original))} {shlex.quote(str(destino))} SALIDA.md")


# --- Frontmatter de la conversión y verificación ------------------------------------------------

CLAVES_VIEJAS = re.compile(r"^(verificado|paginas_con_errores|verificacion_agente\w*|verificacion_juan):")


def partir(texto):
    """(frontmatter sin los ---, cuerpo). Frontmatter '' si no hay."""
    m = re.match(r"---\n(.*?\n)?---\n", texto, re.S)
    return ((m[1] or ""), texto[m.end():]) if m else ("", texto)


def valores(fm):
    """Lectura mínima de YAML plano: escalares, listas en línea y listas en bloque."""
    d, clave = {}, None
    for linea in fm.splitlines():
        m = re.match(r"^([\w-]+):\s*(.*)$", linea)
        if m:
            clave, v = m[1], m[2].strip()
            if v.startswith("[") and v.endswith("]"):
                d[clave] = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
            elif v == "":
                d[clave] = []
            else:
                d[clave] = v.strip("\"'")
        elif clave and re.match(r"^\s+-\s*", linea) and isinstance(d.get(clave), list):
            d[clave].append(re.sub(r"^\s+-\s*", "", linea).strip().strip("\"'"))
    return d


def sin_claves(fm):
    """El frontmatter sin las claves de verificación (con sus listas en bloque)."""
    salida, saltando = [], False
    for linea in fm.splitlines(keepends=True):
        if CLAVES_VIEJAS.match(linea):
            saltando = True
            continue
        if saltando and re.match(r"^\s+-", linea):
            continue
        saltando = False
        salida.append(linea)
    return "".join(salida)


def md5(texto):
    texto = unicodedata.normalize("NFC", texto.replace("\r\n", "\n")).strip()
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def secciones(cuerpo):
    """{página: texto de esa página, con su marca} según las marcas <!-- pág N -->."""
    marcas = list(MARCA_PAGINA.finditer(cuerpo))
    return {int(m[1]): cuerpo[m.start():(marcas[i + 1].start() if i + 1 < len(marcas) else len(cuerpo))]
            for i, m in enumerate(marcas)}


def huella_tramo(cuerpo, paginas):
    sec = secciones(cuerpo)
    faltan = [p for p in paginas if p not in sec]
    if faltan:
        return None, faltan
    return md5("".join(sec[p] for p in paginas)), []


def original_de(ruta, fm, forzado=None):
    if forzado:
        return Path(forzado).expanduser().resolve()
    fuente = valores(fm).get("fuente")
    return (ruta.parent / fuente).resolve() if isinstance(fuente, str) and fuente else None


def total_paginas(original):
    if original and original.is_file():
        t = textos_por_pagina(original)
        return len(t) if t is not None else None
    return None


def vigencia(ruta, forzado=None):
    """Lo que vale HOY de la verificación anotada, recalculando el md5."""
    texto = ruta.read_text(encoding="utf-8")
    fm, cuerpo = partir(texto)
    d = valores(fm)
    actual = md5(cuerpo)
    original = original_de(ruta, fm, forzado)
    n = total_paginas(original)
    estado = d.get("verificacion_agente") if isinstance(d.get("verificacion_agente"), str) else None
    anotado = d.get("verificacion_agente_md5")
    errores = {int(x) for x in d.get("verificacion_agente_errores") or [] if str(x).isdigit()}
    miradas, tramos_validos = set(), []
    motivo = ""
    if estado in ("ok", "con-errores"):
        paginas = d.get("verificacion_agente_paginas")
        tramos = d.get("verificacion_agente_tramos") or []
        if anotado == actual:
            if paginas == "todas":
                miradas = set(range(1, (n or 0) + 1)) if n else {"todas"}
            elif isinstance(paginas, str):
                miradas = set(leer_rango(paginas))
            tramos_validos = list(tramos)
        else:
            for t in tramos:
                rango, _, h = t.rpartition(" ")
                if huella_tramo(cuerpo, leer_rango(rango))[0] == h:
                    tramos_validos.append(t)
                    miradas |= set(leer_rango(rango))
            motivo = "el cuerpo cambió después de marcar" + (
                f"; siguen vigentes los tramos {', '.join(t.rpartition(' ')[0] for t in tramos_validos)}" if tramos_validos else "")
        errores &= miradas if "todas" not in miradas else errores
    elif "verificado" in d:
        motivo = "esquema viejo (verificado:), vale como pendiente"
    return {
        "texto": texto, "fm": fm, "cuerpo": cuerpo, "valores": d, "md5": actual, "anotado": anotado,
        "original": original, "n": n, "estado": estado or "pendiente", "miradas": miradas,
        "errores": errores, "tramos": tramos_validos, "motivo": motivo,
        "juan": d.get("verificacion_juan") == "true" and anotado == actual,
        "juan_caducada": d.get("verificacion_juan") == "true" and anotado != actual,
    }


def cubre(v, paginas):
    """¿La verificación vigente del agente cubre esas páginas (None = el documento entero) sin errores?"""
    if "todas" in v["miradas"]:
        return not v["errores"] and (paginas is None or not (set(paginas) & v["errores"]))
    objetivo = set(paginas) if paginas else (set(range(1, v["n"] + 1)) if v["n"] else None)
    if not objetivo:
        return False
    return objetivo <= v["miradas"] and not (objetivo & v["errores"])


def leer_informe(ruta):
    """{página: (ok?, detalle)} de las líneas `pág N: ok` / `pág N: problema — …`."""
    resultado = {}
    for linea in Path(ruta).expanduser().read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\W*p[áa]g\.?\s*(\d+)\s*:\s*(ok\b|problema\b)(.*)$", linea.strip(), re.I)
        if m:
            i, ok = int(m[1]), m[2].lower() == "ok"
            previo = resultado.get(i, (True, ""))
            resultado[i] = (previo[0] and ok, (previo[1] + " " + m[3].strip(" —-:")).strip())
    return resultado


def escribir_campos(ruta, fm, cuerpo, campos):
    fm = sin_claves(fm)
    if fm and not fm.endswith("\n"):
        fm += "\n"
    ruta.write_text("---\n" + fm + "\n".join(campos) + "\n---\n" + (cuerpo if cuerpo.startswith("\n") else "\n" + cuerpo),
                    encoding="utf-8")


def cmd_marcar(a):
    ruta = Path(a.archivo).expanduser().resolve()
    v = vigencia(ruta, a.original)
    hoy = date.today().isoformat()
    # verificacion_juan: ningún agente la pone en true. Se conserva sólo si el cuerpo no cambió desde la
    # última marca; si cambió (o no había marca), queda en false.
    juan = "true" if v["valores"].get("verificacion_juan") == "true" and v["anotado"] == v["md5"] else "false"
    if v["valores"].get("verificacion_juan") == "true" and juan == "false":
        print("verificacion_juan: el cuerpo cambió desde que Juan la tildó → vuelve a false")

    if a.pendiente:
        campos = ["verificacion_agente: pendiente", f"verificacion_agente_fecha: {hoy}",
                  f'verificacion_agente_md5: "{v["md5"]}"', f"verificacion_juan: {juan}"]
        escribir_campos(ruta, v["fm"], v["cuerpo"], campos)
        print(f"{ruta.name}: " + ", ".join(campos))
        return

    if not a.revision:
        sys.exit("marcar necesita --revision INFORME.txt (una línea `pág N: ok|problema — …` por página mirada) o --pendiente")
    n, original = v["n"], v["original"]
    if not n:
        sys.exit(f"no pude contar las páginas del original ({original}); pasalo con --original")
    tramo = leer_rango(a.paginas) if a.paginas else list(range(1, n + 1))
    if tramo[-1] > n:
        sys.exit(f"el original tiene {n} páginas y el tramo llega a {tramo[-1]}")
    # El informe tiene que ser posterior a la última modificación del .md: uno viejo habla de otro texto.
    if Path(a.revision).expanduser().stat().st_mtime < ruta.stat().st_mtime:
        sys.exit(f"el informe {a.revision} es anterior a la última modificación de {ruta.name}: "
                 "habla de otro texto. Revisá las páginas de nuevo.")
    informe = leer_informe(a.revision)
    faltan = [p for p in tramo if p not in informe]
    if faltan:
        sys.exit(f"el informe no dice nada de {len(faltan)} págs del tramo: {rangos(faltan)}. "
                 "Un ok exige haber mirado TODAS: revisalas y volvé a marcar (o marcá un tramo más chico).")
    errores_tramo = {p for p in tramo if not informe[p][0]}
    if tramo != list(range(1, n + 1)) and huella_tramo(v["cuerpo"], tramo)[0] is None:
        sys.exit(f"verificar por tramos necesita marcas `<!-- pág N -->` en el .md, y faltan las de "
                 f"{rangos(huella_tramo(v['cuerpo'], tramo)[1])}. Las pone el modo transcribir; una conversión "
                 "de anydoc o markitdown se verifica entera.")

    # Guarda: ninguna herramienta saca bien la matemática de LaTeX. Si la conversión no es una
    # transcripción, una página con fuentes de matemática no puede quedar ok aunque el informe lo diga.
    conversor = str(v["valores"].get("conversor", ""))
    if original.suffix.lower() == ".pdf" and not conversor.startswith(TRANSCRIPCION):
        forzadas = [p for p in fuentes_mate(original, tramo) if p not in errores_tramo]
        if forzadas:
            errores_tramo |= set(forzadas)
            print(f"GUARDA: {len(forzadas)} págs con fuentes de LaTeX ({rangos(forzadas)}) y la conversión es de "
                  f"«{conversor or 'desconocido'}», no una transcripción → cuentan como error aunque el informe diga ok. "
                  "Para esas páginas: transcribir desde la imagen.")

    completo = tramo == list(range(1, n + 1))
    if completo:
        miradas_txt, tramos, errores = "todas", [], errores_tramo
    else:
        h, sin_marca = huella_tramo(v["cuerpo"], tramo)
        if h is None:
            sys.exit(f"verificar por tramos necesita marcas `<!-- pág N -->` en el .md, y faltan las de {rangos(sin_marca)}. "
                     "Las pone el modo transcribir; una conversión de anydoc o markitdown se verifica entera.")
        # Se conservan los tramos anteriores que siguen vigentes y no se pisan con este.
        tramos = [t for t in v["tramos"] if not set(leer_rango(t.rpartition(" ")[0])) & set(tramo)]
        tramos.append(f"{rangos(tramo).replace(', ', ',')} {h}")
        tramos.sort(key=lambda t: leer_rango(t.rpartition(" ")[0])[0])
        miradas = set()
        for t in tramos:
            miradas |= set(leer_rango(t.rpartition(" ")[0]))
        errores = (v["errores"] & miradas) - set(tramo) | errores_tramo
        completo = miradas >= set(range(1, n + 1))
        miradas_txt = "todas" if completo else rangos(sorted(miradas))
    estado = "con-errores" if errores else "ok"
    campos = [f"verificacion_agente: {estado}", f"verificacion_agente_fecha: {hoy}",
              f'verificacion_agente_paginas: {"todas" if miradas_txt == "todas" else chr(34) + miradas_txt + chr(34)}',
              f"verificacion_agente_errores: [{', '.join(map(str, sorted(errores)))}]",
              f'verificacion_agente_md5: "{v["md5"]}"']
    if tramos:
        campos.append("verificacion_agente_tramos: [" + ", ".join(f'"{t}"' for t in tramos) + "]")
    campos.append(f"verificacion_juan: {juan}")
    escribir_campos(ruta, v["fm"], v["cuerpo"], campos)
    print(f"{ruta.name}: " + "\n  ".join([""] + campos))
    for p in sorted(errores_tramo):
        if not informe[p][0]:
            print(f"  pág {p}: {informe[p][1]}")


def cmd_estado(a):
    ruta = Path(a.archivo).expanduser().resolve()
    v = vigencia(ruta, a.original)
    paginas = leer_rango(a.paginas) if a.paginas else None
    print(f"{ruta.name}" + (f" · págs {rangos(paginas)}" if paginas else ""))
    anotado = v["valores"].get("verificacion_agente", "—")
    miradas = "todas" if "todas" in v["miradas"] or (v["n"] and v["miradas"] >= set(range(1, v["n"] + 1))) \
        else (rangos(sorted(v["miradas"])) or "ninguna")
    print(f"  agente: anotado {anotado} · vigente: miradas {miradas}, errores [{', '.join(map(str, sorted(v['errores'])))}]"
          + (f" · {v['motivo']}" if v["motivo"] else " · md5 vigente" if v["anotado"] == v["md5"] else ""))
    print("  juan: " + ("verificada" if v["juan"] else
                        "tildada pero el cuerpo cambió después → vale como pendiente" if v["juan_caducada"] else "sin verificar"))
    ok = v["estado"] in ("ok", "con-errores") and cubre(v, paginas)
    print(f"  ingerible: {'sí' if ok else 'NO'}" + ("" if ok else " — hace falta verificacion_agente en ok, vigente y sin errores en "
                                                          + (f"págs {rangos(paginas)}" if paginas else "todo el documento")))
    print(f"  wiki: {'definitiva' if v['juan'] else 'provisional (falta la verificación de Juan)'}")
    h = huella_tramo(v["cuerpo"], paginas)[0] if paginas and secciones(v["cuerpo"]) else v["md5"]
    print(f"  huella: {h}" + (f" (tramo {rangos(paginas)})" if paginas and secciones(v['cuerpo']) else " (cuerpo)"))
    sys.exit(0 if ok else 1)


def cmd_huella(a):
    cuerpo = partir(Path(a.archivo).expanduser().read_text(encoding="utf-8"))[1]
    if a.paginas and secciones(cuerpo):
        h, faltan = huella_tramo(cuerpo, leer_rango(a.paginas))
        if h is None:
            sys.exit(f"faltan las marcas de {rangos(faltan)}")
        print(h)
    else:
        print(md5(cuerpo))


def cmd_ensamblar(a):
    original, dir_ = Path(a.original).expanduser().resolve(), Path(a.dir).expanduser()
    salida = Path(a.salida).expanduser()
    nuevas = {int(re.search(r"\d+", f.stem)[0]): f.read_text(encoding="utf-8").strip()
              for f in sorted(dir_.glob("pag-*.md"))}
    if not nuevas:
        sys.exit(f"no hay pag-NNN.md en {dir_}")
    vacias = [p for p, t in nuevas.items() if not t]
    if vacias:
        sys.exit(f"páginas vacías: {rangos(vacias)} (una página en blanco se transcribe como `[página en blanco]`)")
    conversor = f"{TRANSCRIPCION} ({a.conversor})" if a.conversor else TRANSCRIPCION
    if salida.exists():
        fm, cuerpo = partir(salida.read_text(encoding="utf-8"))
        sec = secciones(cuerpo)
        if not sec and cuerpo.strip() and not a.reemplazar:
            sys.exit(f"{salida.name} ya tiene un cuerpo sin marcas de página (una conversión de herramienta). "
                     "Con --reemplazar se cambia entero por la transcripción; lo anterior queda en git.")
        if not sec:
            sec = {}
        sec.update({p: f"<!-- pág {p} -->\n\n{t}\n\n" for p, t in nuevas.items()})
        fm = re.sub(r"^conversor:.*\n", "", fm, flags=re.M) + f"conversor: {conversor}\n"
    else:
        sec = {p: f"<!-- pág {p} -->\n\n{t}\n\n" for p, t in nuevas.items()}
        fm = (f"tipo: conversión\nfuente: \"{original.name}\"\nconversor: {conversor}\n"
              f"revisado: {date.today().isoformat()}\n")
    cuerpo = "".join(sec[p] if sec[p].endswith("\n\n") else sec[p].rstrip("\n") + "\n\n" for p in sorted(sec))
    salida.write_text("---\n" + fm + "---\n\n" + cuerpo.rstrip("\n") + "\n", encoding="utf-8")
    print(f"{salida.name}: {len(nuevas)} págs escritas ({rangos(sorted(nuevas))}); el .md tiene {rangos(sorted(sec))}")
    print("La transcripción todavía no está verificada: db.py verificar --paginas … y marcar, con OTRO subagente.")


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

    s = sub.add_parser("verificar")
    s.add_argument("--paginas", help="tramo a verificar (1-24); por defecto, todas")
    s.add_argument("--imagenes", help="renderiza TODAS las páginas del tramo en este directorio")
    s.add_argument("--dpi", type=int, default=DPI_REVISION)
    s.add_argument("original")
    s.add_argument("salida")
    s.set_defaults(f=cmd_verificar)

    s = sub.add_parser("transcribir")
    s.add_argument("--paginas", help="tramo a transcribir (un capítulo); por defecto, todas")
    s.add_argument("--dpi", type=int, default=DPI_TRANSCRIBIR)
    s.add_argument("original")
    s.add_argument("dir")
    s.set_defaults(f=cmd_transcribir)

    s = sub.add_parser("ensamblar")
    s.add_argument("--reemplazar", action="store_true", help="pisa un cuerpo sin marcas de página")
    s.add_argument("--conversor", default="", help="modelo que transcribió, p. ej. claude-opus-5-5")
    s.add_argument("original")
    s.add_argument("dir")
    s.add_argument("salida")
    s.set_defaults(f=cmd_ensamblar)

    s = sub.add_parser("marcar")
    s.add_argument("archivo")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--revision", help="informe de la revisión visual: `pág N: ok` o `pág N: problema — …`")
    g.add_argument("--pendiente", action="store_true", help="deja la verificación del agente en pendiente")
    s.add_argument("--paginas", help="tramo mirado (1-24); por defecto, todas")
    s.add_argument("--original", help="si el frontmatter no tiene fuente:")
    s.set_defaults(f=cmd_marcar)

    s = sub.add_parser("estado")
    s.add_argument("--paginas")
    s.add_argument("--original")
    s.add_argument("archivo")
    s.set_defaults(f=cmd_estado)

    s = sub.add_parser("huella")
    s.add_argument("--paginas")
    s.add_argument("archivo")
    s.set_defaults(f=cmd_huella)

    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
