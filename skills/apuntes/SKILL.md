---
name: apuntes
description: Mantiene la wiki de cada materia de la facultad en la bóveda (~/Boveda), con el patrón LLM Wiki de Karpathy. Tiene cuatro operaciones. Ingerir lee una fuente teórica de la cátedra (teoría o bibliografía, entera o por rango de páginas, como un capítulo), sólo si su conversión tiene la verificación del agente en ok, y actualiza el resumen, los conceptos, el índice y el registro; las prácticas, los parciales y las notas del usuario no se ingieren. Consultar responde con citas contra la wiki y guarda la respuesta si el usuario lo pide. Repasar toma preguntas de los parciales y las prácticas, deja que el usuario responda y lo corrige contra la fuente, sin resumir. Revisar busca contradicciones, afirmaciones viejas, conceptos sin página, citas que no valen y diferencias con la página gemela de otra materia, y marca páginas como verificadas cuando el usuario las aprueba. Usar cuando el usuario pida ingerir material o un capítulo de una materia, estudiar, repasar, practicar para un parcial o preguntar algo de una materia que tiene wiki, guardar una respuesta como síntesis o guía de parcial, revisar una wiki o dar por verificada una página.
---

# Apuntes: una wiki por materia

Mantenés la wiki de una materia. Las fuentes son del usuario y sólo las leés. La wiki la escribís
vos entera, y el usuario la lee para estudiar. Hablás y escribís en el idioma del usuario.

El éxito del piloto es **que el usuario la use para estudiar**, no que la wiki quede completa. Ante
la duda, elegí lo que sirve para estudiar: definiciones claras, relaciones entre conceptos, ejemplos
y lo que puede tomarse en un parcial.

**El LLM no estudia por el usuario.** Quien practica con un LLM sin límites rinde peor cuando se lo
sacan. Por eso el usuario tiene su propia carpeta (`Mis notas/`), el repaso pregunta en vez de
resumir, y ninguna página vale como verificada hasta que la aprueba él.

## Estructura

La estructura la decide `bibliotecario` y está en `~/Boveda/AGENTS.md`. Leelo antes de escribir
nada. Si contradice algo de esta skill, manda `AGENTS.md`: avisale al usuario de la diferencia.

```
Areas/Facultad/<carrera>/<materia>/
├── <materia>.md              nota central: la portada de la materia (ver Nota central)
├── Teorias/  Bibliografia/   fuentes de la wiki: PDF y su conversión .md al lado. SÓLO LECTURA
├── Practicas/  Parciales/    material de Repasar, no se ingiere. SÓLO LECTURA
├── Clases/                   notas de clase del usuario, las trae `cierre`. NO ES FUENTE. SÓLO LECTURA
├── Mis notas/                lo que escribe el usuario por su cuenta. NO ES FUENTE. LEÉS, NUNCA ESCRIBÍS
└── Wiki/                     la escribís sólo vos
    ├── index.md              catálogo: cada página con un resumen de una línea, por sección
    ├── log.md                ## [AAAA-MM-DD] ingest|query|repaso|lint|verify | <título>
    ├── Fuentes/              Resumen - <fuente>.md, una por fuente ingerida
    ├── Conceptos/            <Concepto>.md, una por concepto
    └── Síntesis/             respuestas que el usuario pidió guardar, guías de parcial
```

- **Qué es fuente de la wiki: sólo el material teórico de la cátedra**, `Teorias/` y
  `Bibliografia/` (las carpetas las fija `AGENTS.md`). Lo demás no se ingiere:
  - `Practicas/` y `Parciales/` son el material de Repasar;
  - `Clases/` y `Mis notas/` son del usuario: están simplificadas y pueden tener errores. No se
    ingieren, no se citan en `Wiki/` y no se usan para responder en Consultar.
- **Una materia tiene wiki si tiene `Wiki/`.** Si te piden ingerir en una materia que todavía no la
  tiene, preguntá antes de crearla. En una carga inicial ya aprobada no hace falta preguntar. Se
  crea con `index.md` y `log.md` vacíos, más las tres carpetas.
- **Nunca modifiques** nada fuera de `Wiki/`, salvo la conversión que genere o marque
  `convertir-documentos` y la nota central de la materia.
- **`Mis notas/` es del usuario.** No la creás, no escribís ahí, no movés ni renombrás nada, ni
  siquiera para corregir un error de tipeo. Hay reglas `deny` que igual lo rechazarían, pero no
  cubren Bash ni la CLI de Obsidian: la regla vale aunque la herramienta te dejara. La leés en
  Repasar y cuando el usuario te lo pide. **No es fuente de la wiki**: no se ingiere ni se cita en
  `Wiki/`. Lo que el usuario escribió puede estar mal, y la wiki se apoya en el material de la
  cátedra.

### Nota central

`<materia>/<materia>.md` es la portada de la materia, y es a donde apunta `materia: "[[<materia>]]"`
en el frontmatter de cada página. **Si falta, creala** la primera vez que trabajes en esa materia
(antes de escribir cualquier página), sin preguntar, y commiteala con lo primero que commitees:

```markdown
---
tipo: materia
carrera: <carrera>
---

# <materia>

- [[Areas/Facultad/<carrera>/<materia>/Wiki/index|Wiki]]: el catálogo de la wiki.
- Fuentes: `Teorias/` y `Bibliografia/`. Repaso: `Practicas/` y `Parciales/`.

## Fuentes por verificar

Conversiones de las que salió la wiki y que todavía no tienen tu verificación (la casilla
`verificacion_juan` de cada `.md`). Mientras no la tengan, las páginas que salieron de ellas son
provisionales.
```

La sección `Fuentes por verificar` la mantenés vos: una línea por conversión ingerida sin la
verificación de Juan vigente, con enlace al `.md` (con ruta completa y alias) y, si se ingirió por
rangos, los rangos que le faltan (`págs. 25–40`). Actualizala en cada Ingerir, en cada Revisar y
cuando Juan dice que verificó algo. El resto de la nota es del usuario: no lo toques.

### Nombres y enlaces

- La página de una fuente se llama `Resumen - <nombre del original sin extensión>`. **Nunca** le
  pongas el mismo nombre que la fuente o su conversión, porque Obsidian reescribe esos enlaces con la
  ruta completa.
- Hay varias wikis en la bóveda, y en todas se repiten `index.md`, `log.md` y conceptos como
  `Vector`. Por eso **todo enlace a una página de `Wiki/` va con la ruta desde la raíz de la bóveda y
  un alias**: `[[Areas/Facultad/Informatica/Conceptos de Sistemas Operativos/Wiki/Conceptos/Proceso|Proceso]]`.
- Un concepto que comparten dos materias tiene una página en cada una, y cada página enlaza a la
  otra en una línea `Ver también en <materia>: …`.
- Las rutas con acentos pueden venir en NFD. Normalizalas a NFC antes de pasárselas a la CLI de
  Obsidian (`python3 -c 'import unicodedata,sys;print(unicodedata.normalize("NFC",sys.argv[1]))' "<ruta>"`).

### Frontmatter

```yaml
---
tipo: concepto | fuente-resumen | síntesis
materia: "[[<materia>]]"          # el nombre de la carpeta de la materia
fuentes: ["[[…]]", "[[…]]"]       # las fuentes de donde sale lo que dice la página
fuentes_md5: ["<original> <todas|a-b> <md5>", …]  # la versión de cada fuente (o tramo) usada
provisional: true | false         # true mientras alguna fuente no tenga la verificación de Juan
estado: sin-verificar | verificado
revisado: AAAA-MM-DD
---
```

`fuentes_md5` lleva una entrada por fuente, o por tramo si se ingirió por rango, con la huella que
imprime `db.py huella [--paginas a-b] <conversión>.md` en el momento de escribir. Si escribís con
dos tramos de la misma fuente, van las dos entradas.

### Estado de verificación

Hay dos dimensiones, y no se mezclan:

- **`provisional`**: si las **fuentes** de la página ya tienen las dos verificaciones. Lo calculás
  vos (ver abajo). Una página nace `provisional: true` salvo que todas sus fuentes tengan la de Juan.
- **`estado`**: si **la página misma** dice bien lo que dicen sus fuentes. Lo aprueba el usuario.

**Provisional.** Cada conversión lleva dos verificaciones contra el original: la del agente y la de
Juan (el esquema está en `convertir-documentos`, «Las dos verificaciones»). Para ingerir alcanza con
la del agente; la de Juan llega después. Por eso:

- Una página es `provisional: true` mientras alguna de sus fuentes (o de sus tramos, si se ingirió
  por rango) no tenga la verificación de Juan vigente. Por cada entrada de `fuentes_md5`, corré
  `python3 ~/Dev/agentes/skills/convertir-documentos/db.py estado [--paginas a-b] <conversión>.md`:
  la línea `wiki:` dice `definitiva` o `provisional`. Juan verifica con la casilla (el documento
  entero) o por tramos.
- **Cuando Juan te dice que verificó un tramo** ("verifiqué el cap. 3", "las págs. 1–24 están
  bien"), anotalo con `db.py juan <conversión>.md --paginas a-b` (si nombra un capítulo, sacá el
  rango del índice y confirmáselo). Es la única forma en que un agente escribe algo de Juan, y sólo
  cuando él lo dice. Después recalculá `provisional` en las páginas que salieron de ese tramo y
  actualizá `Fuentes por verificar`. Si dice que verificó el documento entero, pedile que tilde la
  casilla `verificacion_juan` en Obsidian.
- **Si Juan encuentra un error en una fuente, no edita el `.md`**: te lo dice. Seguí «Si Juan
  encuentra un error» de `convertir-documentos` (corregir desde la imagen, verificar con otro
  subagente, que Juan vuelva a verificar). El md5 cambia, y las páginas que salieron de ese tramo se
  rehacen (Revisar, chequeo 8).
- **Una página `provisional` no puede ser `verificado`.** Si el usuario la aprueba, decile qué fuentes
  le faltan verificar.

**Estado.** Las conversiones ya se verifican, pero lo que sintetizás encima no. Si un error entra a
una página y otras lo citan, se propaga por toda la wiki. El `estado` corta esa cadena.

- **Toda página que escribís nace `sin-verificar`.** Nunca la marcás `verificado` por tu cuenta.
- **Sólo pasa a `verificado` cuando el usuario lo dice** ("la leí, está bien", "marcá verificada
  Proceso"). Antes corrés los chequeos 4, 5, 6, 8 y 9 de Revisar sobre esa página. Si alguno falla,
  no la marcás: le decís qué cita falla y por qué.
- **Si cambiás el contenido de una página `verificado`, vuelve a `sin-verificar`**, y en el mensaje
  final se lo decís al usuario con la lista de esas páginas. No hace falta en cambios que no tocan lo
  que afirma: enlaces, la línea `Ver también`, el formato.

### Citas

**Toda afirmación del cuerpo lleva su cita.** Si no la podés citar, no la escribas.

- En un PDF, la cita enlaza a la página, porque Obsidian abre el PDF ahí:
  `([[Tema 3 - Memoria - 1.pptx.pdf#page=14|diap. 14]])`. Usá `diap.` en diapositivas y `pág.` en
  el resto.
- Lo que leíste de la imagen de la página, y no de la conversión, se marca así: `([[Tema 3 - Memoria - 1.pptx.pdf#page=14|diap. 14]], de la imagen)`.
- Una deducción tuya que no está en ninguna fuente va marcada con `(inferencia)`, y sólo en
  `Síntesis/`.
- **Nunca cites el `.md` de una conversión.** La conversión es una herramienta para leer; la cita
  apunta siempre al original (el PDF con `#page=`, o el pptx/docx). Si la conversión se regenera, la
  cita sigue valiendo, y lo que el usuario abre es lo que dio la cátedra.

### Copia textual

Las **definiciones**, los **enunciados de teoremas** y las **condiciones de validez** (hipótesis,
"vale si…", "sólo para…") se copian **textuales**, con su cita, nunca parafraseados. Es la misma regla
que las fórmulas, extendida al texto: una paráfrasis cambia justo lo que se toma en un parcial.

```markdown
> **Definición** (Física 2). Un campo es conservativo si la circulación sobre toda curva
> cerrada es nula. ([[Teoria 4.pdf#page=7|pág. 7]])
```

- Van en cita (`>`), en negrita la clase (Definición, Teorema, Condición). Tu explicación va afuera
  de la cita, después.
- Si la página tiene matemática, el texto se copia **de la imagen** o de una transcripción
  verificada (que es una lectura de la imagen), y la cita lo dice (`, de la imagen`).
- Si la fuente la dice de dos formas (por ejemplo la teoría y la práctica), copiá las dos con sus
  citas. No las unifiques.

### Matemática

Las fórmulas se escriben en LaTeX (`$…$` y `$$…$$`) y **siempre desde la imagen del PDF**, nunca
desde el texto de una conversión de herramienta (anydoc, markitdown), que las rompe. Hay dos formas
válidas: leer la página como imagen con `Read` y el parámetro `pages`, o copiarla de una
transcripción (`conversor: transcripción desde la imagen`) con la verificación del agente en `ok`,
que ya se comparó símbolo por símbolo contra la imagen. En las dos, la cita lleva `, de la imagen`.
Una fuente con matemática que sólo tiene conversión de herramienta no pasa el control de Ingerir:
hay que transcribirla primero.

## Ingerir

Entrada: una fuente de `Teorias/` o `Bibliografia/` (un PDF u otro original, o su conversión),
entera o **con un rango de páginas** (`mod2_apunte.pdf págs. 1–24`; ver Por rango). Si te piden
ingerir una práctica, un parcial, una nota de `Clases/` o de `Mis notas/`, no lo hagas: decí que no
son fuente de la wiki y ofrecé Repasar o Consultar.

0.  **Nota central.** Si falta `<materia>/<materia>.md`, creala (ver Nota central).
1.  **Control de la fuente. Sin la verificación del agente en `ok` no se ingiere nada.**
    - Si la fuente es un original sin su `.md` al lado, corré `convertir-documentos` entera: si es un
      PDF con ecuaciones, su modo transcribir, y en los dos casos su paso de verificar.
    - Después, siempre, con el rango pedido si hay uno:
      `python3 ~/Dev/agentes/skills/convertir-documentos/db.py estado [--paginas a-b] <conversión>.md`.
      **Si sale con 1, no ingieras**: decile al usuario por qué, con la línea
      `agente:` que imprime (pendiente, con errores en tales páginas, o el cuerpo cambió después de
      marcar), y qué hace falta (verificar, corregir o transcribir esas páginas y volver a
      verificar). Ofrecé hacerlo, pero la verificación tiene que terminar en `ok` antes de seguir.
    - Anotá la línea `huella:` para `fuentes_md5`, y la línea `juan:` para `provisional`.
2.  **Leer.** Leé la conversión entera, o el tramo del rango. La fuente ya está verificada página por
    página, así que el texto y la matemática de una transcripción se pueden usar tal cual (ver
    Matemática). Las figuras están en bloques `> [!figura]`, con su texto y su descripción, y
    también se verificaron: lo que dice el bloque se puede usar. Si necesitás afirmar de una figura
    algo que el bloque no dice, leela como imagen (hasta 10 por ingesta) y citala `, de la imagen`.
    De una figura que no miraste no afirmes más que lo que dice su bloque.
3.  **Ideas centrales.** Elegí de 3 a 5.
    - **En una ingesta suelta**, mostráselas al usuario en un mensaje y esperá que las corrija: es el
      único momento en que participa.
    - **Por lotes**, no preguntes, salvo que la fuente contradiga algo que ya está en la wiki. En ese
      caso anotá la pregunta para el final.
4.  **Resumen de la fuente.** Escribí `Wiki/Fuentes/Resumen - <fuente>.md` con estas secciones:
    - las ideas centrales;
    - un resumen por sección de la fuente, con citas;
    - los conceptos que toca, con sus enlaces.

    En el frontmatter, `fuentes_md5` y `provisional` salen del paso 1.
5.  **Conceptos.** Actualizá las páginas de los conceptos que toca la fuente y creá las que falten.
    Una fuente puede tocar 10 a 15 páginas. Las nuevas nacen `sin-verificar`, y las `verificado`
    cuyo contenido cambies vuelven a `sin-verificar` (ver Estado de verificación). En cada página
    que toques, agregá o actualizá la entrada de esta fuente en `fuentes_md5` y recalculá
    `provisional`. **No borres lo que ya estaba**:
    - si la fuente nueva lo amplía, integralo;
    - si lo contradice, dejá las dos versiones con sus citas bajo `> [!warning] Contradicción` y
      decíselo al usuario.
6.  **`index.md`, `log.md` y nota central.** En la nota central, agregá la conversión a `Fuentes por
    verificar` si no tiene la verificación de Juan.
    - En `index.md`, una línea por página nueva y la línea actualizada de cada página cambiada.
    - En `log.md`, una entrada `## [AAAA-MM-DD] ingest | <fuente>` (con rango:
      `## [AAAA-MM-DD] ingest | <fuente> págs. a–b`) que liste las páginas tocadas.
7.  **Revisión liviana.** Revisá sólo las páginas que tocaste: enlaces que no resuelven,
    afirmaciones sin cita, citas a una conversión y definiciones parafraseadas.
8.  **Commit.** Hacé un commit por fuente, o por rango:
    `git -C ~/Boveda commit -m 'wiki(<materia>): ingerir <fuente>' -- <rutas tocadas>` (con rango,
    `ingerir <fuente> págs. a–b`). Las rutas son las de `Wiki/` y la conversión si la creaste o la
    verificaste, nunca `git add -A`. Si la conversión ya estaba commiteada y la regeneraste o la
    verificaste, el commit lleva el trailer `Reconversion: si`, como dice `convertir-documentos`.

### Por rango (un capítulo)

Los apuntes largos, como la bibliografía, se ingieren de a un capítulo, cuando el usuario llega a
ese tema. Es una ingesta suelta: el usuario corrige las ideas centrales.

- **Entrada:** la fuente y el rango de páginas. Si el usuario nombra un capítulo, sacá el rango del
  índice del apunte y confirmáselo antes de leer.
- **Un solo resumen por fuente**: `Wiki/Fuentes/Resumen - <fuente>.md` crece con una sección por
  rango ingerido, en el orden de la fuente. No se crea un resumen por capítulo.
- El resumen lleva una sección `Rangos ingeridos`, con una línea por rango: `págs. a–b · AAAA-MM-DD`.
  Antes de ingerir, mirala: si el rango pisa uno ya ingerido, decíselo al usuario y preguntá si
  reingerís ese tramo.
- **El control del paso 1 es por rango**: alcanza con que el agente haya verificado ese tramo
  (`estado --paginas a-b`), aunque el resto de la fuente no lo esté. Verificar por tramos necesita una
  conversión con marcas de página: una transcripción, o una conversión de herramienta pasada por
  `db.py paginar`.
- El tope de 10 figuras leídas como imagen se cuenta **por rango**.
- `log.md` y el commit llevan el rango (pasos 6 y 8).

### Por lotes (carga inicial)

Es para cuando el usuario pide ingerir todo el material de una o más materias.

- Hacé una fuente a la vez, en el orden del curso (Tema 1, Tema 2, …): primero `Teorias/` y
  después `Bibliografia/`, si el usuario la incluyó en la carga. Un commit por fuente.
- **Al terminar la primera materia, pará** y mostrá tres páginas de ejemplo (un resumen, un concepto
  y el `index.md`). Seguí con las demás sólo cuando el usuario apruebe el formato: si hay que
  corregirlo, conviene hacerlo antes de gastar en el resto.
- Si se corta a la mitad, `log.md` dice qué fuentes ya se ingirieron y se retoma desde ahí.

## Consultar

1.  Leé el `index.md` de la materia. Después, las páginas que necesites, y bajá a la fuente cuando
    la wiki no alcance. Las notas de `Clases/` y `Mis notas/` no sirven para responder.
2.  Respondé con citas, igual que en la wiki. Si la wiki no tiene la respuesta, decilo, y si la
    fuente sí la tiene, ofrecé ingerir esa fuente o esa parte. Si la respuesta sale de páginas
    `sin-verificar`, decilo en una línea.
3.  Registrá cada consulta en `log.md` (`## [AAAA-MM-DD] query | <pregunta resumida>`), aunque no se
    guarde. **Es la medida del piloto.**
4.  **Sólo si el usuario lo pide** ("guardalo", "armame una guía para el parcial"), escribí la
    respuesta en `Wiki/Síntesis/<título>.md` con `tipo: síntesis`, agregala a `index.md` y hacé un
    commit `wiki(<materia>): síntesis <título>`.

## Repasar

El usuario practica y vos preguntás y corregís. **No resumís**: si en medio del repaso pide un
resumen o "explicame el tema", decile que eso es Consultar y preguntale si corta el repaso.

1.  **Tema.** Preguntá qué repasa, si no lo dijo: un tema, un módulo o un parcial.
2.  **Preguntas desde los parciales y las prácticas.** Usá las dos carpetas (las fija `AGENTS.md`,
    hoy `Parciales/` y `Practicas/`):
    - `Parciales/` da **el estilo de examen**: el tipo de lo que se toma. Si piden demostrar, que
      demuestre; si piden calcular, un ejercicio.
    - `Practicas/` da **los ejercicios del tema**.
    - Las fotos de `Parciales/` (jpg, jpeg) se leen como imagen con `Read`. Los PDF, por su
      conversión, y como imagen si tienen matemática.
    - Si falta una de las dos carpetas, decilo y seguí con la otra.
3.  **Una por vez.** Hacé una pregunta, **sin la respuesta y sin pistas**, y esperá. Si el usuario
    se traba, la pista la pide él.
4.  **Corregir contra la fuente.** Decí qué está bien, qué falta y qué está mal, con cita. Usá
    **sólo páginas `verificado` o la fuente** (la teoría, la bibliografía, o el enunciado y la
    resolución de la práctica o del parcial; el PDF, leído como imagen si hay matemática). **De una
    conversión, sólo si `db.py estado` dice que la verificación del agente está en `ok` y vigente**;
    si no, leé el PDF como imagen. Una
    página `sin-verificar` no sirve para corregir, porque puede tener justo el error que estás
    buscando: andá a la fuente que cita.
5.  **`Mis notas/` y `Clases/`.** Si el usuario tiene notas del tema, leelas y, al corregir, señalá
    dónde difieren de la fuente, con cita. No las corregís: se lo decís. Nunca corregís al usuario
    con ellas.
6.  **Cierre.** Al terminar, listá las preguntas con un bien / a medias / mal para cada una, y los
    temas a volver a mirar. Registralo en `log.md` como `## [AAAA-MM-DD] repaso | <tema>`, con
    ese resultado. Como Consultar, es medida del piloto.

## Revisar

Revisás el contenido de la wiki. **No** revisás lo estructural (huérfanas, enlaces rotos, páginas
sin `fuentes:`, ubicación): eso es de `bibliotecario`.

Buscás:
1.  contradicciones entre páginas;
2.  afirmaciones que una fuente más nueva dejó viejas;
3.  conceptos que se mencionan en tres o más páginas y no tienen página propia;
4.  **citas que no son fuente**: ninguna cita puede apuntar a `Clases/`, `Mis notas/`,
    `Practicas/` ni `Parciales/`. Se corrige citando la teoría o la bibliografía, o se saca la
    afirmación;
5.  **citas a conversiones**: ninguna cita puede apuntar a un `.md` con `tipo: conversión`. Se
    corrige apuntando al original, a la misma página;
6.  **`verificado` y `provisional` a la vez**: una página no puede ser `verificado` si alguna de sus
    fuentes (o tramos) no tiene la verificación de Juan vigente (`db.py estado [--paginas a-b]`,
    línea `wiki:`). Recalculá
    `provisional` en todas las páginas y actualizá `Fuentes por verificar` de la nota central. Si una
    página `verificado` resulta provisional, vuelve a `sin-verificar`;
7.  **divergencia con la página gemela**: por cada página con `Ver también en <materia>`, abrí la
    gemela y compará sobre todo las definiciones y las condiciones textuales. Si difieren, no
    elijas vos: mostrale las dos, con sus citas, y el usuario decide si es un error o el enfoque de
    la cátedra. Si es enfoque, anotalo en las dos páginas con `> [!note] Enfoque de la cátedra` y
    la cita de cada una. Si es error, se corrige la página que lo tiene;
8.  **fuente que cambió**: por cada entrada de `fuentes_md5`, compará su md5 con el que imprime hoy
    `db.py huella [--paginas a-b] <conversión>.md`. Si difiere, la conversión cambió (por ejemplo,
    se corrigió un error que encontró Juan): esa página, y lo que dice de esa fuente, **se rehace** desde la
    conversión nueva, que antes tiene que volver a pasar el control de Ingerir paso 1. Proponé la
    lista de páginas a rehacer; al rehacerlas vuelven a `sin-verificar`;
9.  **matemática sin `, de la imagen`**: una página con LaTeX (`$`) cuyas citas a esa fuente no
    dicen `, de la imagen`. La regla ya existía (Matemática) y la wiki de Matemática C la incumplió
    en todas sus citas. Se corrige verificando la fórmula contra la imagen o la transcripción
    verificada y agregando la marca.

Presentá los hallazgos en una lista numerada con la corrección propuesta para cada uno. Aplicá sólo
las que el usuario apruebe. Registrá la revisión en `log.md` como `lint` y hacé un commit
`wiki(<materia>): revisar`.

**Marcar `verificado`.** Cuando el usuario aprueba una página, corré sobre ella los chequeos 4, 5, 6,
8 y 9. Si pasan, cambiá `estado` a `verificado` y `revisado` a la fecha de hoy, registralo en `log.md`
(`## [AAAA-MM-DD] verify | <páginas>`) y hacé un commit `wiki(<materia>): verificar <páginas>`.

## Lo que esta skill no hace

- No toca las fuentes, las notas de clase ni `Mis notas/`.
- No ingiere prácticas, parciales, notas de clase ni `Mis notas/`, ni los cita en la wiki.
- No marca una página `verificado` sin que el usuario la apruebe, ni una `provisional`.
- No ingiere una fuente sin la verificación del agente en `ok` y vigente.
- No toca `verificacion_juan` de una conversión: la tilda sólo Juan.
- No resume en un repaso.
- No mueve ni renombra notas fuera de `Wiki/`.
- No procesa la inbox: eso lo hace `cierre`.
- No crea wikis en materias que el usuario no esté cursando.
