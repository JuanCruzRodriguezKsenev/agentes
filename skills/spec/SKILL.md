---
name: spec
description: Convierte una historia de usuario en una especificación por refinamiento de supuestos. Asume lo que falta, lista los supuestos agrupados, y sobre los que el usuario rechaza pregunta uno a uno con alternativas concretas hasta cerrar la spec. Usar cuando el usuario pida armar, definir o refinar una spec o especificación, cuando traiga una historia de usuario para desarrollar, o cuando invoque /spec. También cuando una ronda de planificación arranca con una funcionalidad cuyas decisiones de producto siguen abiertas.
---

# Spec driven development por refinamiento de supuestos

Convertís una historia de usuario en una especificación escrita. El método es
asumir agresivamente y después dejar que el usuario corrija: es mucho más rápido
para él rechazar un supuesto concreto que responder una pregunta abierta.

Este skill **termina cuando la spec está escrita**. No hacés plan técnico, no
partís en tareas y no implementás nada, salvo que el usuario lo pida aparte.

Si corrés dentro de un agente que planifica (por ejemplo `tanda`), la spec es la
entrada de su plan: al terminar le devolvés el control con la ruta de la spec,
sin empezar a planificar vos.

Escribís y hablás en el idioma del usuario.

## Flujo

```
0. Contexto        Explorar el repo si lo hay
1. Draft interno   Redactar la spec en tu cabeza y extraer supuestos
2. Listado         Mostrar solo los supuestos, agrupados y numerados
3. Selección       El usuario dice cuáles no le gustan
4. Ronda de preguntas   Decisiones una por una; los hechos se averiguan o se miden
5. Re-listado      Volver a 3 si el usuario rechaza algo más
6. Escritura       spec.md
```

### Paso 0 — Contexto

Si no te dieron historia de usuario, pedila antes de nada.

Si el directorio actual es un repositorio, explorá **antes** de asumir: stack y
versiones, convenciones de nombres, cómo se resuelve hoy algo parecido, patrones
de manejo de errores y de autenticación, tests existentes. Un supuesto anclado
en el código real vale diez sacados del aire. Acotá la exploración a lo que la
historia toca; no leas el repo entero.

Leé también las instrucciones del proyecto (`AGENTS.md`, `CLAUDE.md`) buscando
dos cosas: **dónde viven las specs** (lo usás en el paso 6) y si ya hay un **doc
de diseño, ADR o spec previa del tema**. Lo que ahí ya está decidido no es un
supuesto: es contexto. Citalo con su ruta y no lo vuelvas a preguntar.

Si no hay repo, saltá este paso sin comentarlo.

Detectá también si hay un runner de BDD instalado (cucumber, behave, pytest-bdd,
godog, SpecFlow). Solo en ese caso vas a emitir feature files al final.

### Paso 1 — Draft interno

Redactá mentalmente la spec completa usando la plantilla de abajo. Cada vez que
tengas que decidir algo que la historia no dice, eso es un supuesto: anotalo.

**No le muestres el draft al usuario.** Leer una spec ya redactada lo ancla y
lo lleva a aceptar supuestos que aislados habría rechazado.

### Paso 2 — Listado de supuestos

Mostrá **solo los supuestos**, agrupados por categoría, con numeración corrida
a lo largo de todos los grupos (para que pueda decir "4, 11, 18").

Categorías, en este orden: Alcance · Actores y permisos · Reglas de negocio ·
Datos · Flujos de error · UX · No funcionales · Integraciones.

Reglas del listado:

- **Máximo 25.** Ordenados por impacto: primero los que cambiarían el diseño si
  estuvieran mal. Una lista de 60 no se lee, se hojea.
- Cada supuesto en una línea, afirmativo y concreto. *"El bloqueo tras intentos
  fallidos dura 15 minutos"*, no *"hay que definir la política de bloqueo"*.
- Un solo supuesto por ítem. Si tiene un "y", probablemente son dos.
- Nada de supuestos triviales de relleno. Si nadie los discutiría, no van.

Cerrá pidiendo los números. Aceptá `2,5,7-9`, `todos`, `ninguno`, y también
descripciones en palabras ("los del bloqueo").

### Paso 3 y 4 — Ronda de preguntas

Antes de preguntar, separá los rechazados en dos clases:

- **Decisión**: la respuesta es una preferencia del usuario (qué ve, qué entra,
  qué pasa en un caso). Esa va a la ronda de preguntas.
- **Hecho**: la respuesta existe afuera y se averigua (cómo se comporta una API,
  qué devuelve una página, qué hace hoy el código). **No la preguntes.** Si se
  resuelve leyendo el repo, leelo y volvé con el dato. Si hace falta medir algo
  que no podés medir desde acá (un navegador con sesión, producción, un servicio
  de terceros), pasalo a **A medir** como `M-n`: qué medir, cómo, y qué decide
  cada resultado posible. Inventar opciones para un hecho es adivinar con formato.

Fijá `N` = cantidad de decisiones rechazadas. Preguntá **una a la vez**, en el
orden de la lista, con `AskUserQuestion`.

- `header`: `P3/7` (entra en 12 caracteres).
- El texto de la pregunta arranca con la barra: `▓▓▓░░░░ P3/7` y sigue con la
  pregunta concreta.
- **4 opciones.** `AskUserQuestion` agrega "Other" solo, no lo agregues vos.

**Reglas duras para las opciones.** Acá es donde este flujo se cae, así que no
las negocies:

- Valores concretos, siempre: `5 intentos`, `15 minutos`, `solo el autor`,
  `Argon2id`. Nunca `configurable`, `depende`, `a definir`, `lo estándar`.
- Mutuamente excluyentes. Si dos opciones pueden ser ciertas a la vez, está mal
  planteada.
- Cada `description` dice **la consecuencia**, no repite el label. El usuario
  elige por consecuencia, no por nombre.
- La primera opción es tu recomendación, con `(Recomendado)` en el label y el
  porqué en la descripción. Recomendá de verdad: si el repo ya resolvió esto de
  cierta forma, esa es la recomendada y decilo.
- Usá `preview` cuando las opciones se entienden mejor vistas: formatos de
  mensaje, estructuras de datos, variantes de layout.

**Regla anti-deriva.** Una respuesta suele abrir supuestos nuevos. Esos **no**
entran en la ronda actual: los anotás como derivados y van a la siguiente. El
denominador de la barra nunca cambia a mitad de camino.

Si el usuario responde con "Other" que eso hay que medirlo, el ítem pasa a A
medir y la barra lo cuenta como respondido.

### Paso 5 — Re-listado

Terminada la ronda, volvé a mostrar la lista completa actualizada: los supuestos
resueltos con su nueva definición, y los derivados que aparecieron, marcados.
Debajo, los `M-n` que quedaron a medir.
Preguntá si queda algo por corregir. Si sí, ronda 2 con el mismo mecanismo. Si
no, decí que **estás listo para crear la especificación** y esperá confirmación.
Si queda un `M-n` del que depende alguna regla, la spec se escribe igual, en
estado `draft`, y cada regla afectada nombra su `M-n`.

### Paso 6 — Escritura

Escribí `spec.md` en la carpeta de specs que declaren las instrucciones del
proyecto (paso 0). Si no declaran ninguna, `specs/<slug>/` en la raíz del repo,
o en el directorio actual si no hay repo. Junto a él dejá `assumptions.md` con
la traza completa.

Si existe un doc de diseño del tema, la spec no repite sus decisiones: las
linkea. Y agregale a ese doc una línea con el link a la spec, para que quien lo
lea sepa que el *qué* vive en otro lado.

Si detectaste un runner de BDD en el paso 0, emití además los escenarios como
`.feature`. Si no hay runner, no lo hagas ni lo ofrezcas: Gherkin dentro del
markdown es el punto óptimo, y una capa de step definitions que nadie corre es
mantenimiento puro.

## Estado y reanudación

Escribí `assumptions.md`, en la carpeta de la spec, **al terminar cada
respuesta**, no al final. Cada ítem con su estado: `asumido` · `rechazado` ·
`resuelto` (con la decisión y el porqué) · `a medir` (con su `M-n`). Así la sesión sobrevive a una compactación o a un corte.

Al invocarte, si ya existe un `assumptions.md` con ítems sin resolver, ofrecé
retomar donde quedó en vez de arrancar de cero.

## Plantilla de la spec

**Núcleo fijo** — va siempre:

| Sección | Contenido |
|---|---|
| Encabezado | Título, estado (`draft`/`aprobada`), fecha |
| Historia | Como *rol* quiero *capacidad* para *beneficio* |
| Contexto y problema | Qué falta hoy y qué se desbloquea |
| Alcance | **Incluye** y **No incluye**, explícito |
| Actores | Tabla de quién puede hacer qué |
| Reglas de negocio | `RN-1..n`, una por línea, verificables |
| Flujos | Camino feliz + tabla de alternativos `A1..n` |
| Datos | Entidades, campos, validaciones, retención |
| Criterios de aceptación | `AC-1..n` en Gherkin |
| Requisitos no funcionales | `NFR-1..n` |
| Supuestos resueltos | Tabla: supuesto → decisión → **por qué** |
| Preguntas abiertas | `PA-1..n`, lo que quedó sin cerrar |

**Secciones condicionales** — solo si se dispara el gatillo:

| Sección | Gatillo |
|---|---|
| Tabla de decisión | Tres o más condiciones se cruzan y el orden de evaluación importa |
| Wireframes ASCII | La historia toca interfaz de usuario |
| Contrato de interfaz | Hay API, evento o CLI: request/response de ejemplo, incluidos los de error |
| Diagrama de estados (Mermaid) | Hay máquina de estados real, no solo pasos |
| Glosario | Aparecen más de cinco términos de dominio |
| Dependencias | Algo tiene que existir antes de poder construir esto |
| Mediciones pendientes | Quedó algún `M-n`: qué medir, cómo, y qué regla decide cada resultado |

Al entregar la spec, decí qué secciones condicionales descartaste y por qué, así
el usuario puede pedir una de vuelta.

**No agregues** riesgos, estimaciones ni métricas de éxito salvo pedido
explícito. Una plantilla con secciones rellenas de "N/A" enseña a hojear en vez
de leer.

## Cómo se escriben los criterios de aceptación

Gherkin, `Dado / Cuando / Entonces`, con datos concretos:

```gherkin
AC-3 — Reintento tras fallo de pago
  Dado un carrito con 2 ítems y una tarjeta rechazada
  Cuando el usuario reintenta con otra tarjeta válida
  Entonces la orden se confirma sin duplicar ítems
    y se registra un solo cargo
```

- El **Entonces** describe algo observable desde afuera. Si menciona una tabla,
  una clase o una función, está mal: eso es implementación.
- Cuando varios escenarios son el mismo con distinto dato, usá
  `Esquema del escenario` con tabla de `Ejemplos`. No es solo ahorro de líneas:
  llenar la tabla te obliga a encontrar casos que en prosa no aparecen.
- Cubrí siempre los caminos de error, no solo el feliz.

## Cómo se dibujan los wireframes

Se dibuja **completo solo el estado base**; para los demás, únicamente la región
que cambia. Lo que especificás no es la estética: es qué muestra cada estado,
dónde, y qué pasa con el foco y con los datos ya escritos.

Enumerá los estados que la prosa esconde: vacío, error, sin permisos, cargando,
enviando, sin resultados. Un wireframe del camino feliz es decoración; los de
error son los que resuelven ambigüedad.

Usá solo caracteres de caja Unicode y mantené las columnas alineadas.

## Criterio de calidad

Las secciones condicionales tienen que **encontrar huecos**, no redibujar lo ya
escrito. Una tabla de decisión que expone un cruce de reglas sin definir se ganó
el lugar; una que reformatea la tabla de actores, no. Si una sección no aportó
nada, sacala antes de entregar.

Cuando termines, señalá al usuario las dos o tres decisiones con más filo de la
spec — las que contradicen a otra regla a propósito, o las que van a doler si
están mal. Esas son las que necesitan su lectura atenta.
