---
name: convertir-documentos
description: Convierte documentos (PDF, Word, PowerPoint, Excel, OpenDocument, RTF, EPUB y correos .msg de Outlook) a Markdown eligiendo entre anydoc y markitdown según una base de pruebas propia, transcribe desde la imagen los PDF con ecuaciones, verifica cada conversión página por página contra el original y la marca con su huella, y registra pruebas nuevas para que la elección mejore con el uso. Usar cuando el usuario pida pasar, convertir o extraer a Markdown uno o más de esos archivos, cuando pregunte qué herramienta conviene para un documento, cuando pida verificar o marcar una conversión o consultar su estado de verificación, o cuando pida medir, comparar o registrar conversiones. No usar para HTML, CSV, JSON, XML, notebooks, código, texto plano, zips, imágenes ni audio.
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
2. Convertir    el comando que imprime; si el PDF tiene ecuaciones, transcribir desde la imagen (2b)
3. Revisar      mirar la salida; limpiar pies si corresponde
4. Verificar    filtro automático + revisión visual de TODAS las páginas (o del tramo) + marcar
5. Registrar    db.py probar + calificar, cuando falta evidencia o lo piden
```

**Cada conversión lleva dos verificaciones contra el original** (Juan, 2026-09-28): primero la del
agente (paso 4), después la de Juan, que la tilda él en Obsidian. **Nada se ingiere ni se resume sin
la del agente en `ok`.** El detalle, en «Las dos verificaciones».

### 1. Recomendar

`db.py recomendar ARCHIVO...` detecta formato y tipo de contenido y responde, por archivo, qué
herramienta usar, en qué nivel de evidencia se basa, con qué confianza y el comando exacto.

Si el tipo detectado está mal (por ejemplo un `.docx` que en realidad es casi todo tablas), repetí con
`--tipo`. Tipos: `texto`, `codigo`, `diapositivas`, `escaneado`, `ecuaciones`, `tablas`, `hoja-calculo`, `libro`,
`correo`, `otro`.

`codigo` **no se detecta solo**: ponelo a mano con `--tipo codigo` en PDF de enunciados o apuntes con
código (Java, assembler…), típicamente exportados de Google Docs. En esos anydoc aplasta el código en
una línea o lo mete en tablas inventadas y markitdown lo deja línea por línea; mezclarlos con los PDF
de prosa esconde la diferencia. Las señales obvias (líneas que terminan en `;`/`{`/`}`, fuentes
monoespaciadas, el generador) no los separan: el assembler de `Practica-1.pdf` no tiene ninguna.

Un PDF sale `ecuaciones` cuando al menos el 30 % de una muestra de sus páginas usa fuentes de
matemática de LaTeX (`CMMI`, `CMEX`, `MSBM`…). **Ninguna herramienta convierte bien la matemática de
LaTeX**: anydoc cambia ∈ por "2" y ∀ por "8" y pierde la "fi" y los acentos; markitdown deja `(cid:88)`
en vez de ∑, separa los acentos e inventa tablas. En Matemática C, las 8 conversiones que se habían
dado por buenas tenían la matemática rota, dos con el sentido cambiado (`i ≠ j` → "i = j", `≤` →
"<"). Si `recomendar` imprime el aviso, **el camino es transcribir desde la imagen (2b)**. Una
conversión de herramienta de un PDF así sirve para buscar, pero `marcar` nunca la deja en `ok` en
las páginas con fuentes de LaTeX. Lo mismo vale para apuntes manuscritos o escaneados que se
quieran usar como fuente.

Cómo decide: si sólo una herramienta soporta la extensión, esa. Si no, busca calificaciones de las dos
en este orden y usa el primer nivel donde haya: mismo formato y tipo → misma familia y tipo → mismo
formato de cualquier tipo (salvo PDF, donde el tipo pesa demasiado). Gana la de mejor calidad media; si
la diferencia es menor a 0,5, la más rápida, y lo informa como **calidad empatada**, no con una
confianza: la confianza sólo dice cuántos casos hay. En un PDF empatado, convertí con las dos, corré
`verificar` sobre cada salida y quedate con la de menos páginas marcadas. En PDF sólo cuentan las filas de markitdown medidas con la versión fijada. Sin calificaciones cae en la regla previa: anydoc, salvo
PDF de diapositivas, que va con markitdown.

### 2. Convertir

Por defecto el `.md` queda **al lado del original, con el mismo nombre**. Si ya existe un `.md` con ese
nombre, preguntá antes de pisarlo. Si está en `~/Boveda` y ya estaba commiteado, el commit lleva el
trailer `Reconversion: si` (ver «Commit en la bóveda»). Para varios archivos, corré las conversiones juntas.

*   anydoc: `pnpm dlx @firecrawl/anydoc ARCHIVO -o SALIDA.md`. **Nunca `npm` ni `npx`.**
*   markitdown: `uvx --from 'markitdown[all]==0.1.5' markitdown ARCHIVO -o SALIDA.md`. **Versión
    fijada**: desde la 0.1.6 pega las palabras en PDF de Google Docs e inventa tablas en PDF de
    diapositivas. No la subas sin medir antes con `probar` (la constante está en `db.py`).

### 2b. Transcribir desde la imagen

Para PDF con ecuaciones (o manuscritos) que van a ser fuente de una wiki. El `.md` lo escribe un
modelo mirando cada página, con la matemática en LaTeX, y queda con una marca `<!-- pág N -->` por
página. Esas marcas permiten verificar e ingerir **por tramos**. Un libro o un apunte largo se
transcribe **capítulo por capítulo**, cuando se lo va a ingerir; no entero de una vez.

1.  `db.py transcribir [--paginas A-B] ORIGINAL <temporal>/trans` renderiza las páginas del tramo a
    150 ppp y lista los lotes de hasta 10 páginas.
2.  **Un subagente `general-purpose` por lote**, porque las imágenes llenan el contexto. Pasale la
    ruta del directorio, las páginas del lote y este encargo:
    > Por cada página N del lote, mirá `pag-NNN.png` y escribí `pag-NNN.md` con su transcripción
    > exacta en Markdown. Reglas: el texto tal cual, en su orden, sin corregir erratas ni completar
    > nada; toda la matemática en LaTeX (`$…$` en línea, `$$…$$` en bloque), símbolo por símbolo
    > (≤ no es <, ≠ no es =, respetá subíndices, exponentes, ∀, ∈, grados); títulos con `#` sólo si
    > en la página son títulos; tablas como tablas Markdown y matrices con `\begin{pmatrix}`; una
    > figura o diagrama, como `[Figura: <qué muestra, en una línea>]`; sin marcas de agua, encabezados
    > ni pies repetidos. Una página en blanco: `[página en blanco]`. Una parte ilegible:
    > `[ilegible]`, nunca una conjetura. No escribas nada más que esos archivos.
3.  `db.py ensamblar [--conversor <modelo>] ORIGINAL <temporal>/trans SALIDA.md` arma el `.md` (o
    reemplaza esas páginas en uno que ya tiene marcas) y pone
    `conversor: transcripción desde la imagen (<modelo>)`. Si el `.md` existente es una conversión de
    herramienta, sin marcas, pide `--reemplazar`: el cuerpo pasa a ser sólo lo transcripto, y lo de
    antes queda en git. Las páginas que no se transcribieron no están en el `.md`.
4.  **Verificá con el paso 4, con OTROS subagentes**, nunca con el que transcribió: quien cometió un
    error tiende a volver a leerlo igual.

### 3. Revisar

*   Mirá el principio de cada salida. Una salida vacía o casi vacía de un PDF casi siempre es un
    escaneado: markitdown sale bien igual, anydoc sale con código 3 (`NeedsOcr`).
*   **Palabras pegadas**: el conversor perdió los espacios (`envíenmensajesaestosobjetos`) y la salida
    no sirve ni para buscar. Lo detecta `verificar` (paso 4). Pasa con las dos herramientas, incluida
    markitdown 0.1.5, aunque en menos casos que desde la 0.1.6. En los formatos que `verificar` no
    cubre, `grep -cP '\p{Ll}{35,}' SALIDA.md` hace el mismo chequeo: con más de tres líneas, la salida
    está dañada.
*   **Escaneados**: ninguna hace OCR local. Avisale al usuario. Las opciones de OCR mandan el documento
    afuera: `--ocr hosted` de anydoc sube el documento **entero** a Firecrawl Parse; el plugin
    `markitdown-ocr` y Azure necesitan un cliente LLM o credenciales. No uses ninguna sin permiso
    explícito.
*   **PDF de diapositivas con markitdown**: repite el pie de página en cada diapositiva. Corré
    `db.py limpiar-pies --paginas N SALIDA.md`, revisá que los candidatos sean pies de verdad y recién
    ahí repetí con `--aplicar`. Deja la primera aparición para no perder la atribución.
*   Lo que está en imágenes (diagramas, UML, capturas de código) se pierde con las dos: mencionalo si el
    documento tiene muchas.

### 4. Verificar

Hacelo **siempre**, con cada conversión o transcripción. Es la verificación del agente: la primera de
las dos (ver «Las dos verificaciones»).

1.  **Filtro automático.** `db.py verificar [--paginas A-B] --imagenes <temporal>/revision ORIGINAL SALIDA.md`.
    Anda con PDF (por página), pptx (por diapositiva) y docx (el documento entero). Con los demás
    formatos imprime que no puede, y ahí revisás a mano. Por cada página:
    *   **cobertura**: qué fracción de las palabras de 3 letras o más aparece en el `.md`. Marca las
        páginas por debajo de 0,9 y detecta texto perdido o dañado;
    *   **símbolos**: los símbolos matemáticos del original que no están en la salida;
    *   **código**: las líneas que terminan en `;`, `{` o `}` y no quedaron como línea en la salida. Es
        el código aplastado, que la cobertura no detecta.
    Además cuenta las palabras pegadas y lista las páginas con fórmulas. **Es un filtro, no un
    veredicto: ninguna métrica alcanza para un `ok`.** La de palabras no ve la matemática, y así se
    marcaron `ok` conversiones rotas.
2.  **Palabras pegadas** → no hace falta mirar nada más: convertí con la otra herramienta y volvé a
    verificar.
3.  **Revisión visual de TODAS las páginas del tramo** (sólo PDF; un pptx o docx se exporta a PDF con
    `soffice --headless --convert-to pdf`). `verificar --imagenes` renderiza todas a 110 ppp y las
    parte en lotes de 10. **El 10 es el tamaño del lote, no un tope**: un documento de 40 páginas son
    4 subagentes. Si son demasiadas para esta sesión, verificá un tramo (`--paginas`) y decíselo al
    usuario; nunca marques `ok` páginas que nadie miró. Un subagente `general-purpose` por lote, con
    las rutas del PDF, del `.md` y de las imágenes, y este encargo:
    > Por cada `pag-NNN.png` de tu lote, mirá la página y buscá su tramo en el `.md` (la marca
    > `<!-- pág N -->`, o un grep de una frase). Compará **todo**: que el texto esté completo y en
    > orden, y la matemática símbolo por símbolo (≤ contra <, ≠ contra =, ∈, ∀, subíndices,
    > exponentes, signos, fracciones, matrices). Buscá también palabras pegadas, código aplastado y
    > tablas inventadas. Respondé **una línea por cada página de tu lote, sin saltear ninguna**:
    > `pág N: ok` o `pág N: problema — <qué, con el texto del .md y lo que dice la imagen>`. No
    > arregles nada.
    Juntá las respuestas de todos los lotes en un archivo de informe temporal.
4.  **Si fallan páginas**: en una conversión de herramienta, convertí con la otra (si soporta el
    formato) y verificá de nuevo; en un PDF con ecuaciones, transcribí esas páginas (2b). En una
    transcripción, corregí la página (otro subagente, desde la imagen), `ensamblar` y verificá esa
    página de nuevo.
5.  **Marcá** con el informe: `db.py marcar SALIDA.md --revision INFORME.txt [--paginas A-B]`.
    *   El estado lo saca del informe: `ok` si todas las páginas miradas dicen ok, `con-errores` si no,
        con la lista de páginas.
    *   **Se niega si al informe le falta alguna página del tramo**, o si el informe es anterior a la
        última modificación del `.md`.
    *   **Guarda de matemática**: si la conversión no es una transcripción, las páginas del PDF con
        fuentes de LaTeX cuentan como error aunque el informe diga ok.
    *   Anota el md5 del cuerpo (sin el frontmatter). Por tramos, además, el md5 de cada tramo; los
        tramos anteriores que siguen iguales se conservan. Verificar por tramos necesita las marcas de
        página, así que sólo anda con transcripciones: una conversión de herramienta se verifica
        entera.
    *   `db.py marcar SALIDA.md --pendiente` la vuelve a `pendiente`, por ejemplo al migrar.
6.  **Consultá** con `db.py estado [--paginas A-B] SALIDA.md`: recalcula el md5 y dice qué vale hoy.
    Sale con 0 sólo si la verificación del agente está en `ok`, vigente y sin errores en esas
    páginas. Es el control que usa `apuntes` antes de ingerir.

### Las dos verificaciones

Van en el frontmatter de cada `.md` convertido. Son claves planas, no un mapa anidado, porque el
panel de propiedades de Obsidian no edita mapas anidados y, al tildar la casilla, reescribe el
frontmatter entero:

```yaml
verificacion_agente: pendiente | ok | con-errores   # la escribe sólo marcar
verificacion_agente_fecha: 2026-09-28
verificacion_agente_paginas: todas                  # o "1-24", si se verificó por tramos
verificacion_agente_errores: [3, 7]
verificacion_agente_md5: "<md5 del cuerpo, sin el frontmatter>"
verificacion_agente_tramos: ["1-24 <md5 del tramo>"] # sólo por tramos
verificacion_juan: false                            # casilla de Obsidian: SÓLO la tilda Juan
```

*   **La huella es del cuerpo**, porque marcar cambia el frontmatter (y Obsidian también).
*   **Si el md5 del cuerpo deja de coincidir, las dos valen como `pendiente`** (salvo los tramos cuyo
    md5 sigue igual). No hace falta resetear nada a mano: `estado` lo recalcula.
*   **Ningún agente pone `verificacion_juan: true`, ni por pedido.** Juan la tilda en Obsidian.
    `marcar` la conserva si el cuerpo no cambió desde la marca anterior, y la pone en `false` si
    cambió. Es lo único que un agente hace con ese campo.
*   La verificación de Juan es por documento entero; no tiene tramos.
*   El esquema viejo (`verificado:` y `paginas_con_errores:`) vale como `pendiente`, y `marcar` lo
    borra al escribir el nuevo.

### Commit en la bóveda: trailer `Reconversion: si`

`~/Boveda` tiene un hook `commit-msg` que rechaza modificar (`M`), renombrar con cambios (`R<100`) o
borrar (`D`) un `*.pdf` o una conversión con la verificación del agente en `ok`, salvo que el mensaje
lleve el trailer `Reconversion: si`. Lo escribe `bibliotecario`; la especificación está en
`AGENTS.md`. (Hasta que `bibliotecario` lo pase al esquema nuevo, el hook mira `verificado: ok`.)

- **Lleva el trailer** el commit que incluye una conversión **que ya estaba commiteada** y que
  regeneraste o transcribiste (pasos 2 y 2b) o reverificaste (paso 4: `marcar` cambia su frontmatter,
y eso es un `M`).
  Para saberlo: `git -C ~/Boveda ls-files --error-unmatch <ruta.md>` sale con 0 si ya estaba.
- **No lo lleva** una conversión nueva (un `A` en git), aunque en el mismo paso la marques.
- Va como último párrafo del mensaje, en una línea propia. Con dos `-m`, git lo arma solo:
  `git -C ~/Boveda commit -m 'conversión: reconvertir <archivo>' -m 'Reconversion: si' -- <rutas>`.
- Es sólo para conversiones. Esta skill **nunca** modifica, renombra ni borra un original: si un
  commit tuyo tocaría un `*.pdf`, pará y avisá.

### 5. Registrar evidencia

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
*   `paginas_marcadas` (`16/37`) y `cobertura_min`: el resumen de `verificar` sobre la salida, que
    `probar` completa solo. Sirve para comparar, pero no reemplaza la calificación.
*   `lote` agrupa una misma tanda; los duelos comparan las dos herramientas sobre el mismo archivo y lote.

`db.py stats [--formato F] [--tipo T]` resume calidad, éxito y velocidad por formato, tipo y herramienta,
y los duelos archivo por archivo. Usalo cuando el usuario pregunte qué herramienta es mejor para algo.

anydoc se mide con el paquete de Node instalado en `~/.local/share/convertir-documentos` (lo instala
`probar` con pnpm si falta).

La base vive en el repo `~/Dev/agentes`: no hagas commit salvo que el usuario lo pida.
