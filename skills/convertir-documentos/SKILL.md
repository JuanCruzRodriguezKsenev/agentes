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
4. Verificar    db.py verificar página por página + revisión visual de una muestra + marcar
5. Registrar    db.py probar + calificar, cuando falta evidencia o lo piden
```

### 1. Recomendar

`db.py recomendar ARCHIVO...` detecta formato y tipo de contenido y responde, por archivo, qué
herramienta usar, en qué nivel de evidencia se basa, con qué confianza y el comando exacto.

Si el tipo detectado está mal (por ejemplo un `.docx` que en realidad es casi todo tablas), repetí con
`--tipo`. Tipos: `texto`, `diapositivas`, `escaneado`, `ecuaciones`, `tablas`, `hoja-calculo`, `libro`,
`correo`, `otro`.

Un PDF sale `ecuaciones` cuando al menos el 30 % de una muestra de sus páginas usa fuentes de
matemática de LaTeX (`CMMI`, `CMEX`, `MSBM`…). **Ninguna herramienta convierte bien la matemática de
LaTeX**: anydoc cambia ∈ por "2" y ∀ por "8" y pierde la "fi" y los acentos; markitdown deja `(cid:88)`
en vez de ∑, separa los acentos e inventa tablas. Si `recomendar` imprime el aviso, **decíselo al
usuario antes de convertir**. Si está de acuerdo, convertí igual con la recomendada y verificá.

Cómo decide: si sólo una herramienta soporta la extensión, esa. Si no, busca calificaciones de las dos
en este orden y usa el primer nivel donde haya: mismo formato y tipo → misma familia y tipo → mismo
formato de cualquier tipo (salvo PDF, donde el tipo pesa demasiado). Gana la de mejor calidad media; si
la diferencia es menor a 0,5, la más rápida. En PDF sólo cuentan las filas de markitdown medidas con la versión fijada. Sin calificaciones cae en la regla previa: anydoc, salvo
PDF de diapositivas, que va con markitdown.

### 2. Convertir

Por defecto el `.md` queda **al lado del original, con el mismo nombre**. Si ya existe un `.md` con ese
nombre, preguntá antes de pisarlo. Para varios archivos, corré las conversiones juntas.

*   anydoc: `pnpm dlx @firecrawl/anydoc ARCHIVO -o SALIDA.md`. **Nunca `npm` ni `npx`.**
*   markitdown: `uvx --from 'markitdown[all]==0.1.5' markitdown ARCHIVO -o SALIDA.md`. **Versión
    fijada**: desde la 0.1.6 pega las palabras en PDF de Google Docs e inventa tablas en PDF de
    diapositivas. No la subas sin medir antes con `probar` (la constante está en `db.py`).

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

Hacelo **siempre**, con cada conversión. El usuario quiere comprobar página por página que el texto se
copió bien.

1.  `db.py verificar --imagenes <temporal>/ORIGINAL ORIGINAL SALIDA.md`. Anda con PDF (por página),
    pptx (por diapositiva) y docx (el documento entero). Con los demás formatos imprime que no puede, y
    ahí revisás a mano. Por cada página:
    *   **cobertura**: qué fracción de las palabras de 3 letras o más aparece en el `.md`. Marca las
        páginas por debajo de 0,9 y detecta texto perdido o dañado;
    *   **símbolos**: los símbolos matemáticos del original que no están en la salida;
    *   **código**: las líneas que terminan en `;`, `{` o `}` y no quedaron como línea en la salida. Es
        el código aplastado, que la cobertura no detecta.
    Además cuenta las palabras pegadas de todo el documento y lista las páginas con fórmulas. Ahí los
    chequeos automáticos no alcanzan a ver si la matemática está bien.
2.  **Palabras pegadas** → no hace falta mirar nada más: convertí con la otra herramienta y volvé a
    verificar.
3.  **Revisión visual** (sólo PDF). `verificar` elige hasta 10 páginas: las marcadas, peores
    primero, más la primera, una del medio, la última y dos con fórmulas. Con `--imagenes` las
    renderiza a 70 ppp. Si quedan marcadas afuera del tope, **no las mires todas**: avisale al usuario
    cuántas son. Delegá la revisión en un subagente `general-purpose`, porque las imágenes llenan el
    contexto. Pasale las rutas del PDF, del `.md` y de las imágenes, y este encargo:
    > Por cada `pag-NNN.png`, mirá la página y buscá su tramo en el `.md` (grep de una frase de la
    > página). Decí si el texto está completo y en orden, si hay palabras pegadas, código aplastado,
    > tablas inventadas o fórmulas rotas. Respondé una línea por página: `pág N: ok` o
    > `pág N: problema — <qué, con un ejemplo textual>`. No arregles nada.
4.  **Si fallan páginas**, convertí con la otra herramienta (si soporta el formato) y verificá de
    nuevo. Quedate con la que tenga menos páginas con problemas. Si fallan las dos, avisale al
    usuario.
5.  **Marcá el resultado** en el frontmatter del `.md` final:
    `db.py marcar SALIDA.md ok` o `db.py marcar SALIDA.md con-errores --paginas 3,7,19`. Si el
    frontmatter ya existe, agrega `verificado` y `paginas_con_errores` sin tocar lo demás. Una página
    que no miraste no va como error: si quedaron marcadas sin revisar, decíselo al usuario.

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
