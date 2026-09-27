---
name: apuntes
description: Mantiene la wiki de cada materia de la facultad en la bóveda (~/Boveda), con el patrón LLM Wiki de Karpathy. Tiene tres operaciones. Ingerir lee una fuente de la materia (PDF, conversión o nota de clase) y actualiza el resumen, los conceptos, el índice y el registro. Consultar responde con citas contra la wiki y guarda la respuesta si el usuario lo pide. Revisar busca contradicciones, afirmaciones viejas y conceptos sin página. Usar cuando el usuario pida ingerir material de una materia, estudiar o preguntar algo de una materia que tiene wiki, guardar una respuesta como síntesis o guía de parcial, o revisar una wiki. También la usa la skill `cierre` para las clases del día.
---

# Apuntes: una wiki por materia

Mantenés la wiki de una materia. Las fuentes son del usuario y sólo las leés. La wiki la escribís
vos entera, y el usuario la lee para estudiar. Hablás y escribís en el idioma del usuario.

El éxito del piloto es **que el usuario la use para estudiar**, no que la wiki quede completa. Ante
la duda, elegí lo que sirve para estudiar: definiciones claras, relaciones entre conceptos, ejemplos
y lo que puede tomarse en un parcial.

## Estructura

La estructura la decide `bibliotecario` y está en `~/Boveda/AGENTS.md`. Leelo antes de escribir
nada. Si contradice algo de esta skill, manda `AGENTS.md`: avisale al usuario de la diferencia.

```
Areas/Facultad/<carrera>/<materia>/
├── Teorias/  Practicas/  …   fuentes: PDF y su conversión .md al lado. SÓLO LECTURA
├── Clases/                   notas de clase del usuario, las trae `cierre`. SÓLO LECTURA
└── Wiki/                     la escribís sólo vos
    ├── index.md              catálogo: cada página con un resumen de una línea, por sección
    ├── log.md                ## [AAAA-MM-DD] ingest|query|lint | <título>
    ├── Fuentes/              Resumen - <fuente>.md, una por fuente ingerida
    ├── Conceptos/            <Concepto>.md, una por concepto
    └── Síntesis/             respuestas que el usuario pidió guardar, guías de parcial
```

- **Una materia tiene wiki si tiene `Wiki/`.** Si te piden ingerir en una materia que todavía no la
  tiene, preguntá antes de crearla. En una carga inicial ya aprobada no hace falta preguntar. Se
  crea con `index.md` y `log.md` vacíos, más las tres carpetas.
- **Nunca modifiques** nada fuera de `Wiki/`, salvo la conversión que genere `convertir-documentos`.

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
revisado: AAAA-MM-DD
---
```

### Citas

**Toda afirmación del cuerpo lleva su cita.** Si no la podés citar, no la escribas.

- En un PDF, la cita enlaza a la página, porque Obsidian abre el PDF ahí:
  `([[Tema 3 - Memoria - 1.pptx.pdf#page=14|diap. 14]])`. Usá `diap.` en diapositivas y `pág.` en
  el resto.
- Lo que leíste de la imagen de la página, y no de la conversión, se marca así: `([[Tema 3 - Memoria - 1.pptx.pdf#page=14|diap. 14]], de la imagen)`.
- En una nota de clase: `([[Clase 2026-09-27 - Conceptos de Sistemas Operativos|clase 27/9]])`.
- Una deducción tuya que no está en ninguna fuente va marcada con `(inferencia)`, y sólo en
  `Síntesis/`.

### Matemática

Las fórmulas se escriben en LaTeX (`$…$` y `$$…$$`) y **siempre desde la imagen del PDF**, nunca
desde el texto de la conversión, que las rompe. Si la conversión tiene `tipo: ecuaciones` o hay
matemática en la página, leé la página como imagen con `Read` y el parámetro `pages`.

## Ingerir

Entrada: una fuente de la materia, que puede ser un PDF u otro original, su conversión o una nota de
`Clases/`.

1.  **Conversión.** Si la fuente es un original sin su `.md` al lado, corré la skill
    `convertir-documentos` entera, incluido su paso de verificar. Si la conversión existe pero no
    tiene `verificado`, corré sólo el paso de verificar. Las notas de clase no se convierten.
2.  **Leer.** Leé la conversión entera. Después leé como imagen **las páginas de
    `paginas_con_errores`** y las que tienen matemática. Esas páginas son justo los diagramas y las
    tablas que la conversión no sacó.
    - Si son más de 10 páginas y estás en una ingesta suelta, preguntá antes de seguir.
    - En una carga por lotes o en el cierre, leé las primeras 10 y anotá las demás en la sección
      `Páginas sin revisar` del resumen.
3.  **Ideas centrales.** Elegí de 3 a 5.
    - **En una ingesta suelta**, mostráselas al usuario en un mensaje y esperá que las corrija: es el
      único momento en que participa.
    - **En `cierre` y por lotes**, no preguntes, salvo que la fuente contradiga algo que ya está en la
      wiki. En ese caso anotá la pregunta para el final.
4.  **Resumen de la fuente.** Escribí `Wiki/Fuentes/Resumen - <fuente>.md` con estas secciones:
    - las ideas centrales;
    - un resumen por sección de la fuente, con citas;
    - los conceptos que toca, con sus enlaces;
    - en una nota de clase, las **dudas del usuario**, cada una con respuesta citada si la wiki ya la
      tiene o como `Abierta` si no;
    - `Páginas sin revisar`, si quedaron.
5.  **Conceptos.** Actualizá las páginas de los conceptos que toca la fuente y creá las que falten.
    Una fuente puede tocar 10 a 15 páginas. **No borres lo que ya estaba**:
    - si la fuente nueva lo amplía, integralo;
    - si lo contradice, dejá las dos versiones con sus citas bajo `> [!warning] Contradicción` y
      decíselo al usuario.
6.  **`index.md` y `log.md`.**
    - En `index.md`, una línea por página nueva y la línea actualizada de cada página cambiada.
    - En `log.md`, una entrada `## [AAAA-MM-DD] ingest | <fuente>` que liste las páginas tocadas.
7.  **Revisión liviana.** Revisá sólo las páginas que tocaste: enlaces que no resuelven y
    afirmaciones sin cita.
8.  **Commit.** En una ingesta suelta o por lotes, hacé un commit por fuente:
    `git -C ~/Boveda commit -m 'wiki(<materia>): ingerir <fuente>' -- <rutas tocadas>`. Las rutas son
    las de `Wiki/` y la conversión nueva, nunca `git add -A`. **Dentro de `cierre` no commitees**:
    commitea `cierre` al final.

### Por lotes (carga inicial)

Es para cuando el usuario pide ingerir todo el material de una o más materias.

- Hacé una fuente a la vez, en el orden del curso (Tema 1, Tema 2, …; primero las teorías y después
  las prácticas), con su commit cada una.
- **Al terminar la primera materia, pará** y mostrá tres páginas de ejemplo (un resumen, un concepto
  y el `index.md`). Seguí con las demás sólo cuando el usuario apruebe el formato: si hay que
  corregirlo, conviene hacerlo antes de gastar en el resto.
- Si se corta a la mitad, `log.md` dice qué fuentes ya se ingirieron y se retoma desde ahí.

## Consultar

1.  Leé el `index.md` de la materia. Después, las páginas que necesites, y bajá a la fuente cuando
    la wiki no alcance.
2.  Respondé con citas, igual que en la wiki. Si la wiki no tiene la respuesta, decilo, y si la
    fuente sí la tiene, ofrecé ingerir esa fuente o esa parte.
3.  Registrá cada consulta en `log.md` (`## [AAAA-MM-DD] query | <pregunta resumida>`), aunque no se
    guarde. **Es la medida del piloto.**
4.  **Sólo si el usuario lo pide** ("guardalo", "armame una guía para el parcial"), escribí la
    respuesta en `Wiki/Síntesis/<título>.md` con `tipo: síntesis`, agregala a `index.md` y hacé un
    commit `wiki(<materia>): síntesis <título>`.

## Revisar

Revisás el contenido de la wiki. **No** revisás lo estructural (huérfanas, enlaces rotos, páginas
sin `fuentes:`, ubicación): eso es de `bibliotecario`.

Buscás tres cosas:
- contradicciones entre páginas;
- afirmaciones que una fuente más nueva dejó viejas;
- conceptos que se mencionan en tres o más páginas y no tienen página propia;
- y, además, las dudas `Abierta` que alguna fuente ingerida después ya responde.

Presentá los hallazgos en una lista numerada con la corrección propuesta para cada uno. Aplicá sólo
las que el usuario apruebe. Registrá la revisión en `log.md` como `lint` y hacé un commit
`wiki(<materia>): revisar`.

## Lo que esta skill no hace

- No toca las fuentes ni las notas de clase.
- No mueve ni renombra notas fuera de `Wiki/`.
- No procesa la inbox: eso lo hace `cierre`.
- No crea wikis en materias que el usuario no esté cursando.
