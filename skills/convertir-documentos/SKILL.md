---
name: convertir-documentos
description: Convierte documentos (PDF, Word, PowerPoint, Excel, OpenDocument, RTF, EPUB y correos .msg de Outlook) a Markdown eligiendo entre anydoc y markitdown según una base de pruebas propia, y registra pruebas nuevas para que la elección mejore con el uso. Usar cuando el usuario pida pasar, convertir o extraer a Markdown uno o más de esos archivos, cuando pregunte qué herramienta conviene para un documento, o cuando pida medir, comparar o registrar conversiones. No usar para HTML, CSV, JSON, XML, notebooks, código, texto plano, zips, imágenes ni audio.
---

# Convertir documentos a Markdown

Dos herramientas, ninguna gana siempre:

*   **anydoc** (Firecrawl, Rust): reconstruye la estructura (títulos, listas, tablas, ecuaciones),
    soporta formatos viejos y ODF, y es mucho más rápida. Con diapositivas en PDF aplasta el código y
    convierte los diagramas en tablas basura.
*   **markitdown** (Microsoft, Python): texto más plano pero fiel al orden y a los saltos de línea;
    mejor con diapositivas que tienen código. No soporta `.doc`, `.ppt`, ODF ni RTF.

La decisión sale de la base `datos/pruebas.csv` de esta skill, a través de `db.py` (sólo Python
estándar). Todo se corre así:

```bash
python3 ~/Dev/agentes/skills/convertir-documentos/db.py <subcomando> ...
```

Hablás y escribís en el idioma del usuario.

## Alcance

| Tipo | Extensiones | anydoc | markitdown |
| :--- | :--- | :---: | :---: |
| Word | `.docx` | sí | sí |
| Word | `.doc`, `.docm` | sí | no |
| PowerPoint | `.pptx` | sí | sí |
| PowerPoint | `.ppt`, `.pps`, `.pot`, `.pptm`, `.ppsx`, `.ppsm` | sí | no |
| Excel | `.xlsx`, `.xls` | sí | sí |
| Excel | `.xlsm`, `.xlsb` | sí | no |
| OpenDocument | `.odt`, `.odp`, `.ods` | sí | no |
| RTF | `.rtf` | sí | no (devuelve el RTF crudo) |
| PDF | `.pdf` | sí | sí |
| EPUB | `.epub` | sí | sí |
| Outlook | `.msg` | no | sí |

Fuera de alcance: HTML, CSV, JSON, XML, `.ipynb`, código, `.txt`/`.md`, imágenes, audio. Un `.zip` se
descomprime y se trata cada documento de adentro. Si el usuario igual quiere convertir algo de eso,
decíselo y no uses esta skill.

## Flujo

```
1. Recomendar   db.py recomendar ARCHIVO...
2. Convertir    el comando que imprime, salvo que el usuario pida otra cosa
3. Revisar      mirar la salida; limpiar pies si corresponde
4. Registrar    db.py probar + calificar, cuando falta evidencia o lo piden
```

### 1. Recomendar

`db.py recomendar ARCHIVO...` detecta formato y tipo de contenido y responde, por archivo, qué
herramienta usar, en qué nivel de evidencia se basa, con qué confianza y el comando exacto.

Si el tipo detectado está mal (por ejemplo un `.docx` que en realidad es casi todo tablas), repetí con
`--tipo`. Tipos: `texto`, `diapositivas`, `escaneado`, `ecuaciones`, `tablas`, `hoja-calculo`, `libro`,
`correo`, `otro`.

Cómo decide: si sólo una herramienta soporta la extensión, esa. Si no, busca calificaciones de las dos
en este orden y usa el primer nivel donde haya: mismo formato y tipo → misma familia y tipo → mismo
formato de cualquier tipo (salvo PDF, donde el tipo pesa demasiado). Gana la de mejor calidad media; si
la diferencia es menor a 0,5, la más rápida. Sin calificaciones cae en la regla previa: anydoc, salvo
PDF de diapositivas, que va con markitdown.

### 2. Convertir

Por defecto el `.md` queda **al lado del original, con el mismo nombre**. Si ya existe un `.md` con ese
nombre, preguntá antes de pisarlo. Para varios archivos, corré las conversiones juntas.

*   anydoc: `pnpm dlx @firecrawl/anydoc ARCHIVO -o SALIDA.md`. **Nunca `npm` ni `npx`.**
*   markitdown: `uvx --from 'markitdown[all]' markitdown ARCHIVO -o SALIDA.md`

### 3. Revisar

*   Mirá el principio de cada salida. Una salida vacía o casi vacía de un PDF casi siempre es un
    escaneado: markitdown sale bien igual, anydoc sale con código 3 (`NeedsOcr`).
*   **Escaneados**: ninguna hace OCR local. Avisale al usuario. Las opciones de OCR mandan el documento
    afuera: `--ocr hosted` de anydoc sube el documento **entero** a Firecrawl Parse; el plugin
    `markitdown-ocr` y Azure necesitan un cliente LLM o credenciales. No uses ninguna sin permiso
    explícito.
*   **PDF de diapositivas con markitdown**: repite el pie de página en cada diapositiva. Corré
    `db.py limpiar-pies --paginas N SALIDA.md`, revisá que los candidatos sean pies de verdad y recién
    ahí repetí con `--aplicar`. Deja la primera aparición para no perder la atribución.
*   Lo que está en imágenes (diagramas, UML, capturas de código) se pierde con las dos: mencionalo si el
    documento tiene muchas.

### 4. Registrar evidencia

Registrá cuando la recomendación no dijo `confianza alta`, cuando el caso cayó en la regla previa, cuando
cambió la versión de alguna herramienta, o cuando el usuario lo pida. Si son muchos archivos parecidos,
alcanza con dos o tres representativos.

1.  `db.py probar --salida <directorio temporal> [--origen ETIQUETA] [--lote NOMBRE] ARCHIVO...`
    Convierte con las dos in-process (una corrida de calentamiento y la mediana de `--rep`, 3 por
    defecto), guarda las dos salidas y agrega una fila por herramienta con la calidad vacía. Usá un
    directorio temporal, nunca la carpeta del usuario.
2.  Compará las dos salidas contra el original (texto del PDF, estructura esperada).
3.  `db.py calificar ID CALIDAD 'nota'` para **cada** fila. La nota dice qué hizo bien o mal, en
    concreto: "código aplastado en una línea", "tablas reales", "pierde las ecuaciones".
4.  Contale al usuario qué filas agregaste y si cambió la recomendación.

No califiques lo que no miraste: si no revisaste una salida, dejá la calidad vacía.

## Escala de calidad

| | |
| :--- | :--- |
| 0 | Inservible: vacía, error, o basura (por ejemplo el formato crudo) |
| 1 | Pierde contenido importante (ecuaciones, secciones, código) |
| 2 | Contenido completo pero desordenado o con estructura inventada que confunde |
| 3 | Texto completo y en orden, sin estructura Markdown útil |
| 4 | Buena estructura con algún error puntual |
| 5 | Estructura fiel: títulos, listas, tablas y énfasis como en el original |

## La base

`datos/pruebas.csv`, una fila por herramienta y archivo. Se modifica **sólo** con `db.py` (`probar`,
`calificar`), nunca a mano.

*   `modo`: `inproc` mide la conversión sola; `cli` incluye el arranque de pnpm o uvx (~1-2 s). Las
    comparaciones de velocidad usan sólo `inproc`.
*   `estado`: `ok`, `vacio`, `necesita_ocr`, `no_soportado`, `error`.
*   `lote` agrupa una misma tanda; los duelos comparan las dos herramientas sobre el mismo archivo y lote.

`db.py stats [--formato F] [--tipo T]` resume calidad, éxito y velocidad por formato, tipo y herramienta,
y los duelos archivo por archivo. Usalo cuando el usuario pregunte qué herramienta es mejor para algo.

anydoc se mide con el paquete de Node instalado en `~/.local/share/convertir-documentos` (lo instala
`probar` con pnpm si falta).

La base vive en el repo `~/Dev/agentes`: no hagas commit salvo que el usuario lo pida.
