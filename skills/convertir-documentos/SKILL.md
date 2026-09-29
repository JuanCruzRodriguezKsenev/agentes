---
name: convertir-documentos
description: Convierte documentos (PDF, Word, PowerPoint, Excel, OpenDocument, RTF, EPUB y correos .msg de Outlook) a Markdown eligiendo entre anydoc y markitdown según una base de pruebas propia, transcribe desde la imagen los PDF con ecuaciones o figuras y las fotos de parciales o prácticas (jpg, png, webp, tif), verifica cada conversión página por página contra el original y la marca con su huella, y registra pruebas nuevas para que la elección mejore con el uso. Usar cuando el usuario pida pasar, convertir o extraer a Markdown uno o más de esos archivos, cuando pregunte qué herramienta conviene para un documento, cuando pida verificar o marcar una conversión o consultar su estado de verificación, o cuando pida medir, comparar o registrar conversiones. No usar para HTML, CSV, JSON, XML, notebooks, código, texto plano, zips, audio ni imágenes que no sean fotos de un documento.
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

Una **foto de un documento** (`.jpg`, `.jpeg`, `.png`, `.webp`, `.tif`, `.tiff`), como la foto de un
parcial, no pasa por ninguna herramienta: se transcribe desde la imagen (2c).

Fuera de alcance: HTML, CSV, JSON, XML, `.ipynb`, código, `.txt`/`.md`, imágenes que no son un
documento, audio. Un `.zip` se descomprime y se trata cada documento de adentro. Si el usuario
igual quiere convertir algo de eso, decíselo y no uses esta skill.

## Flujo

```
1. Recomendar   db.py recomendar ARCHIVO...
2. Convertir    el comando que imprime; si tiene ecuaciones o figuras, transcribir desde la imagen (2b)
                una foto (jpg, png…): transcribir desde la foto (2c)
3. Revisar      mirar la salida; limpiar pies si corresponde
4. Verificar    filtro automático + revisión visual de TODAS las páginas (o del tramo) + marcar
5. Registrar    db.py probar + calificar, cuando falta evidencia o lo piden
```

**Lo que se exige es el contenido, no la presentación** (Juan, 2026-09-29). Tiene que estar, y
fiel: el texto, palabra por palabra; las fórmulas, símbolo por símbolo, con mayúsculas y minúsculas
(`v` no es `V`, la O no es el 0); y los esquemas, tablas y diagramas con toda su información. No
importa, y no se transcribe ni se verifica: el color, la alineación, si un título estaba centrado,
sangrías, viñetas, cómo se escribe una tabla o se parte una fórmula en renglones. El formato del
original puede ser malo; se formatea después, como convenga.

**Rápido por defecto**: transcriptores y verificadores son subagentes con `model: "sonnet"`, **todos
los lotes lanzados juntos en un mismo mensaje**, no de a uno. Medido en Matemática C (2026-09-28):
sonnet ~8 s por página con el contenido casi al nivel de Opus; Gemini Flash ~30 min por página y el
triple de errores de contenido. Ampliar una zona es para un símbolo que de verdad no se puede decidir,
no una rutina por página.

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

Para PDF con ecuaciones (o manuscritos) y para las páginas con figuras (ver «Figuras»: casi todas
las presentaciones), cuando van a ser fuente de una wiki. El `.md` lo escribe un modelo mirando cada
página, con la matemática en LaTeX y cada figura en un bloque, y queda con una marca `<!-- pág N -->`
por página. Esas marcas permiten verificar e ingerir **por tramos**. Un libro o un apunte largo se
transcribe **capítulo por capítulo**, cuando se lo va a ingerir; no entero de una vez. Se puede
transcribir **una sola página** (`--paginas 7`): sirve para arreglar la página que falló.

1.  `db.py transcribir [--paginas A-B] ORIGINAL <temporal>/trans` renderiza las páginas del tramo a
    150 ppp, lista los lotes de hasta 10 páginas y las páginas con imágenes.
2.  **Un subagente `general-purpose` con `model: "sonnet"` por lote**, porque las imágenes llenan el
    contexto, y **todos los lotes en paralelo**. Pasale la ruta del directorio, las páginas del lote y
    este encargo:
    > Por cada página N del lote, mirá `pag-NNN.png` y escribí `pag-NNN.md` con su transcripción
    > exacta en Markdown. **Importa el contenido, no la presentación**: el texto tal cual, en su
    > orden, sin corregir erratas ni completar nada; toda la matemática en LaTeX (`$…$` en línea,
    > `$$…$$` en bloque), símbolo por símbolo (≤ no es <, ≠ no es =, `v` no es `V`, la O no es el 0;
    > respetá subíndices, exponentes, ∀, ∈, grados, flechas); tablas y matrices completas. El
    > formato (títulos, alineación, sangrías, viñetas, cómo partir una fórmula) elegilo vos, sin
    > copiar el del original; sacá marcas de agua, encabezados y pies repetidos. **Cada esquema,
    > diagrama, gráfico, tabla o código que sea imagen** va en su lugar como un bloque
    > `> [!figura] <Clase>: <qué muestra>`, con una línea `> Texto:` que copia **todo** el texto
    > que tiene adentro y una descripción de lo que dice que no está en ese texto; el formato
    > completo está en «Figuras» de la skill convertir-documentos. Un adorno sin información no
    > hace falta.
    > Una página en blanco: `[página en blanco]`. Una parte ilegible: `[ilegible]`, nunca una
    > conjetura. **Sólo si un símbolo no se puede decidir a la vista, ampliá**: `pdftoppm -r 400 -f N -l N
    > -png ORIGINAL <temporal>/zoom` y recortá la zona con `magick … -crop`. Si dos glifos se ven
    > iguales en esa letra (la O y el 0, la l y el 1), desempatá con la capa de texto
    > (`pdftotext -f N -l N -layout ORIGINAL -`): sirve **sólo para elegir entre los glifos que
    > estás viendo**, nunca para copiar texto. Si tampoco la capa lo resuelve, elegí por contexto y
    > dejá al lado `<!-- dudoso: <qué opciones>, elegido por contexto -->`. Si el original **no
    > tiene dibujado** algo que el texto evidentemente pide (un ∈ que falta, un hueco), no lo
    > completes: `[falta en el original: <qué parece faltar>]`. No escribas nada más que esos
    > archivos.
3.  `db.py ensamblar [--conversor <modelo>] ORIGINAL <temporal>/trans SALIDA.md` arma el `.md` (o
    reemplaza esas páginas en uno que ya tiene marcas) y pone
    `conversor: transcripción desde la imagen (<modelo>)`. Si el `.md` existente es una conversión de
    herramienta, sin marcas, pide `--reemplazar`: le agrega las marcas (como `paginar`, abajo),
    reemplaza las páginas transcriptas y **conserva las demás** como texto de herramienta, cada una
    con la marca `<!-- pág N · sin transcribir: <conversor> -->`. Así el documento se sigue pudiendo
    buscar entero, y esas páginas cuentan como no verificadas hasta que se las transcriba y verifique
    (las guardas de matemática y de figuras las miran como texto de herramienta).
    *   `db.py paginar SALIDA.md` agrega esas marcas a una conversión de herramienta sin transcribir
        nada: con los saltos de página que deja markitdown, o alineando cada párrafo con el texto de
        su página. Hace falta para verificar por tramos una conversión de herramienta. Cambia el
        cuerpo, así que la verificación anterior deja de valer.
4.  **Verificá con el paso 4, con OTROS subagentes**, nunca con el que transcribió: quien cometió un
    error tiende a volver a leerlo igual.

**Al volver a transcribir** una página que falló (o una conversión vieja), el transcriptor nuevo
**no lee el `.md` anterior**: sólo la imagen. Si lo lee, copia el error. Lo que sí se pasa es la
lista de errores conocidos, **al verificador**, como "mirá especialmente": así se confirma que no
volvieron.

**Los lotes** se arman por documento entero (un documento no se parte salvo que pase de 10
páginas) y **por tipo**: los manuscritos juntos, el LaTeX tipeado junto, las presentaciones juntas.
Cada lote lleva un contexto común y los difíciles no se mezclan con los fáciles.

### 2c. Fotos de un documento

Provisorio (2026-09-29), hasta que haya herramientas propias para imágenes. Para fotos de parciales o
de prácticas. `db.py` cuenta cada foto como **un original de 1 página**, así que `ensamblar`, `marcar`,
`estado` y `huella` andan igual que con un PDF. En cambio, `recomendar`, `transcribir` y `verificar` no
sirven para imágenes: no hay nada que renderizar ni capa de texto.

1.  El `.md` va al lado de la foto, con el mismo nombre (`2025-04-22 Tema 1.jpeg` →
    `2025-04-22 Tema 1.md`). Un examen en varias fotos no se une: cada foto tiene su `.md`.
2.  **Un subagente `general-purpose`** mira la foto y escribe `<temporal>/trans/pag-001.md`, con el
    mismo encargo de 2b (LaTeX, figuras en `> [!figura]`, `[ilegible]`, `<!-- dudoso: … -->`). Ampliar
    ante la duda es recortar la foto con `magick ORIGINAL -crop …`. Además, **la foto no es una página
    limpia**: se transcribe sólo lo impreso o escrito del documento, y no la mesa ni los dedos. Lo que
    alguien escribió a mano encima de un enunciado impreso (una resolución, una nota o un tachón) se
    transcribe aparte, en un bloque `> [!figura] Anotación a mano: …`, nunca mezclado con el enunciado.
    Lo que la foto corta o deja fuera de foco va como `[fuera de la foto]` o `[ilegible]`.
3.  `db.py ensamblar --conversor <modelo> FOTO <temporal>/trans SALIDA.md` arma el `.md`, con la marca
    `<!-- pág 1 -->` y `fuente:` apuntando a la foto.
4.  **Verificá con OTRO subagente**, con el encargo de revisión visual del paso 4 aplicado a la foto
    en lugar de `pag-NNN.png`. El informe es una sola línea, `pág 1: ok · figuras: K` (o
    `pág 1: problema — … · figuras: K`), y después va `db.py marcar --revision INFORME SALIDA.md`. No hay
    filtro automático: `verificar` avisa que el formato no se verifica y no hace nada más.
5.  La verificación de Juan es la de siempre: la tilda él en Obsidian.

**Una resolución no es una conversión.** Si el usuario pide además resolver el examen, la resolución
va en otra nota, que no lleva `tipo: conversión` ni `fuente:`, y nunca en el `.md` de la foto. Los
parciales no se ingieren en la wiki: esto sirve para buscar en ellos y para Repasar.

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
*   Lo que está en imágenes (diagramas, UML, capturas de código) se pierde con las dos. **Una figura
    perdida es un error de la conversión** (ver «Figuras»): esas páginas se transcriben (2b).

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
    Además cuenta las palabras pegadas, lista las páginas con fórmulas y las páginas con imágenes, y
    avisa cuáles de estas no tienen ningún bloque `[!figura]` en el `.md` (para mirar: puede ser un
    adorno). **Es un filtro, no un
    veredicto: ninguna métrica alcanza para un `ok`.** La de palabras no ve la matemática, y así se
    marcaron `ok` conversiones rotas.
2.  **Palabras pegadas** → no hace falta mirar nada más: convertí con la otra herramienta y volvé a
    verificar.
3.  **Revisión visual de TODAS las páginas del tramo** (sólo PDF; un pptx o docx se exporta a PDF con
    `soffice --headless --convert-to pdf`; si `soffice` no está instalado, decíselo al usuario: sin
    PDF no hay revisión visual ni transcripción). `verificar --imagenes` renderiza todas a 110 ppp y las
    parte en lotes de 10. **El 10 es el tamaño del lote, no un tope**: un documento de 40 páginas son
    4 subagentes. Si son demasiadas para esta sesión, verificá un tramo (`--paginas`) y decíselo al
    usuario; nunca marques `ok` páginas que nadie miró. Un subagente `general-purpose` con
    `model: "sonnet"` por lote, **todos en paralelo**, distinto del que transcribió, con las rutas del
    PDF, del `.md` y de las imágenes, y este encargo:
    > Por cada `pag-NNN.png` de tu lote, mirá la página y buscá su tramo en el `.md` (la marca
    > `<!-- pág N -->`, o un grep de una frase). **Compará sólo el contenido**: que el texto esté
    > completo y en orden, y la matemática símbolo por símbolo (≤ contra <, ≠ contra =, ∈, ∀,
    > subíndices, exponentes, signos, fracciones, matrices, mayúsculas y minúsculas: `v` no es `V`).
    > La presentación no es un problema: títulos, alineación, sangrías, viñetas, cómo está escrita
    > una tabla o partida una fórmula. Buscá también palabras pegadas, código aplastado y tablas
    > inventadas. **Contá los esquemas, diagramas, gráficos, tablas o código que sean imagen** (los
    > adornos sin información y la plantilla no cuentan) y, por cada uno, buscá su bloque
    > `> [!figura]` en esa página del `.md`: que la línea `Texto:` tenga **todo** su texto (cada
    > rótulo, valor, nombre de eje o de nodo) y que la descripción diga bien lo que muestra (qué se
    > conecta con qué, hacia dónde, qué valores). Uno sin bloque, o con un rótulo de menos, es un
    > problema. **Si un símbolo no se puede decidir a la vista, ampliá** (`pdftoppm -r 400 -f N -l N`
    > y `magick … -crop`). Si dos glifos se ven iguales en esa letra (la O y el 0), la capa de
    > texto (`pdftotext -f N -l N -layout`) desempata. Un `[falta en el original: …]` es correcto
    > si en la imagen ampliada ahí no hay nada dibujado; un `<!-- dudoso: … -->` no es un
    > problema, pero anotalo en tu línea para que llegue a Juan.
    > Respondé **una línea por cada página de tu lote, sin saltear ninguna**:
    > `pág N: ok · figuras: K` o `pág N: problema — <qué, con el texto del .md y lo que dice la
    > imagen> · figuras: K`, con K = las figuras con información que viste (0 si ninguna). No
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
    *   **Se niega si una línea no dice `figuras: K`**: sin la cuenta no se sabe si se perdió alguna.
    *   **Guarda de matemática** (estricta, Juan 2026-09-28): las páginas que siguen siendo texto de
        herramienta (toda la conversión, o las marcadas `sin transcribir`) y usan fuentes de LaTeX
        cuentan como error aunque el informe diga ok.
    *   **Guarda de figuras**: una página cuenta como error si el verificador vio más figuras con
        información que bloques `[!figura]` tiene esa página en el `.md`. Si el original tiene
        imágenes y la página ningún bloque, `marcar` sólo lo avisa: puede ser un adorno.
    *   Anota el md5 del cuerpo (sin el frontmatter). Por tramos, además, el md5 de cada tramo; los
        tramos anteriores que siguen iguales se conservan. Verificar por tramos necesita las marcas de
        página: las tiene una transcripción, y a una conversión de herramienta se las pone `paginar`.
    *   `db.py marcar SALIDA.md --pendiente` la vuelve a `pendiente`, por ejemplo al migrar.
6.  **Consultá** con `db.py estado [--paginas A-B] SALIDA.md`: recalcula el md5 y dice qué vale hoy.
    Sale con 0 sólo si la verificación del agente está en `ok`, vigente y sin errores en esas
    páginas. Es el control que usa `apuntes` antes de ingerir.

### Figuras

**Un esquema, tabla o diagrama perdido es un error de contenido** (Juan, 2026-09-29; reemplaza la
regla del 2026-09-28 que exigía también los adornos). Una figura es un esquema, diagrama, gráfico,
captura, foto o ilustración con información, o una tabla o código que están como imagen. Un adorno
sin información y la plantilla (el fondo, las franjas y los logos que se repiten) no hacen falta.

En una transcripción, cada figura va **en su lugar del texto**, como un callout de Obsidian:

```markdown
> [!figura] Gráfico: reflexión de la base canónica respecto del eje x
> Texto: «y» · «x» · «Reflexión respecto del eje x» · «$e_2$» · «$e_1$=L($e_1$)» · «L($e_2$)»
> Ejes cartesianos: x horizontal, y vertical. Desde el origen, tres vectores del mismo largo:
> $e_1$ en rojo sobre el eje x hacia la derecha; $e_2$ en azul hacia arriba; $L(e_2)$ en violeta
> hacia abajo. Arriba a la derecha, un recuadro con el texto «Reflexión respecto del eje x».
```

*   **Título**: la clase y qué muestra, en una línea. Clases: `Diagrama`, `Gráfico`, `Captura`,
    `Foto`, `Ilustración`, `Tabla`, `Código`.
*   **`Texto:`** copia todo el texto que la figura tiene adentro, en orden de lectura, cada trozo
    entre «», con la matemática en LaTeX. `Texto: —` si no tiene. Es lo que la hace buscable y lo que
    el verificador compara rótulo por rótulo.
*   **Descripción**: lo que la figura dice y el texto no. Un diagrama: cada nodo y cada relación
    (`A → B`, con el rótulo de la flecha). Un gráfico: ejes, escalas, cada curva o vector, los puntos
    notables con sus valores. Una tabla como imagen: la tabla en Markdown dentro del callout. Una
    captura de código: el código en un bloque dentro del callout.
El chequeo es doble: el verificador visual cuenta las figuras de cada página y revisa cada bloque
(paso 4.3), y `marcar` compara esa cuenta con los bloques de la página (paso 4.5). El filtro automático sólo ve imágenes: un diagrama dibujado con formas lo
encuentra únicamente la revisión visual.

El bloque no incluye la imagen. Si más adelante se decide guardar recortes, van como una línea
`> ![[…]]` dentro del mismo bloque, sin cambiar el resto.

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
verificacion_juan_tramos: ["1-24 <md5 del tramo>"]  # tramos que Juan DIJO que verificó
```

*   **La huella es del cuerpo**, porque marcar cambia el frontmatter (y Obsidian también).
*   **Si el md5 del cuerpo deja de coincidir, las dos valen como `pendiente`** (salvo los tramos cuyo
    md5 sigue igual). No hace falta resetear nada a mano: `estado` lo recalcula.
*   **Ningún agente pone `verificacion_juan: true`, ni por pedido.** Juan la tilda en Obsidian, y
    vale para el documento entero. `marcar` la conserva si el cuerpo no cambió desde la marca
    anterior, y la pone en `false` si cambió. Es lo único que un agente hace con ese campo.
*   **La verificación de Juan por tramos** va en `verificacion_juan_tramos`, con el md5 de cada
    tramo. La escribe un agente **sólo cuando Juan lo dice explícitamente** ("verifiqué el cap. 3",
    "las págs. 1–24 están bien"), con `db.py juan SALIDA.md --paginas A-B`. Se niega si la
    verificación del agente no está en `ok` y vigente para ese tramo: Juan verifica después. Un tramo
    de Juan sigue vigente mientras no cambie su md5, aunque se transcriban o se sumen otras páginas;
    `marcar` conserva los vigentes y borra los que cambiaron. `estado --paginas` lo usa en la línea
    `juan:` y en `wiki:` (definitiva o provisional).
*   El esquema viejo (`verificado:` y `paginas_con_errores:`) vale como `pendiente`, y `marcar` lo
    borra al escribir el nuevo.

### Si Juan encuentra un error

**Juan no edita el `.md`** (decidido por tanda, 2026-09-28: Juan no edita archivos crudos). Te dice
qué está mal y dónde:

1.  Corregí esas páginas desde la imagen: transcribilas de nuevo (2b, `--paginas` con esas páginas)
    y `ensamblar`. Si la conversión era de herramienta, esas páginas pasan a ser transcripción.
2.  Verificalas con **otro** subagente (paso 4), no con el que corrigió, y `marcar` con
    `--paginas`.
3.  Decile a Juan qué cambió, para que vuelva a verificar. Su casilla, o su tramo si el error estaba
    ahí, ya cayó sola: cambió el md5.
4.  En la bóveda, las páginas de wiki que salieron de ese tramo se rehacen (apuntes, Revisar,
    chequeo 8).

### Commit en la bóveda: trailer `Reconversion: si`

`~/Boveda` tiene un hook `commit-msg` que rechaza modificar (`M`), renombrar con cambios (`R<100`) o
borrar (`D`) un `*.pdf` o una conversión verificada en `HEAD`, salvo que el mensaje lleve el trailer
`Reconversion: si`. Un `M` que cambia **sólo el frontmatter** (el cuerpo es igual en `HEAD` y en el
índice) pasa sin trailer: es lo que hacen `marcar`, `juan` y la casilla de Juan en Obsidian. Lo
escribe `bibliotecario`; la especificación está en `AGENTS.md`. (Mientras `bibliotecario` no lo pase
al esquema nuevo, el hook mira `verificado: ok` y no tiene la excepción: ahí cualquier `M` sobre una
protegida lleva el trailer.)

- **Lleva el trailer** el commit que cambia el **cuerpo** de una conversión **que ya estaba
  commiteada**: la regeneraste, la transcribiste, la paginaste o la corregiste (pasos 2 y 2b,
  `paginar`, «Si Juan encuentra un error»). Para saberlo:
  `git -C ~/Boveda ls-files --error-unmatch <ruta.md>` sale con 0 si ya estaba. Ante la duda,
  ponelo: sobra, pero no rompe nada.
- **No lo lleva** una conversión nueva (un `A` en git), aunque en el mismo paso la marques, ni un
  commit que sólo cambia el frontmatter (con el hook nuevo).
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
