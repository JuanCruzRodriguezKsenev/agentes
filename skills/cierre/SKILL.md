---
name: cierre
description: Procesa la inbox de la bóveda (~/Boveda/Inbox) al final del día con un solo comando. Lleva cada nota de clase a su materia y la ingiere en la wiki con la skill `apuntes`. Reparte el archivo general, que tiene ideas, pendientes, links y lo que el usuario hizo, entre la lista de pendientes, las ideas y el diario del día, y deja todo en un solo commit. Usar cuando el usuario pida cerrar el día, procesar o vaciar la inbox, o invoque /cierre.
---

# Cierre del día

Procesás la inbox del usuario al final del día, en una sola pasada. Resolvés solo lo obvio, juntás lo
dudoso en **una sola ronda de preguntas** y terminás con un resumen de qué fue a dónde y un commit.
Tiene que ser corto: se corre todos los días. Hablás y escribís en el idioma del usuario.

## Rutas

Las rutas las decide `bibliotecario` y están en `~/Boveda/AGENTS.md`. Leelo al arrancar. Si alguna
de estas no coincide con lo que dice ahí, manda `AGENTS.md`: usá esa y avisá.

| Qué | Dónde |
| :--- | :--- |
| Inbox | `Inbox/`: una nota por clase, con cualquier nombre que indique la materia, más `Inbox/General.md` |
| Notas de clase procesadas | `<materia>/Clases/Clase AAAA-MM-DD - <materia>.md` |
| Diario | `Areas/Diario/AAAA-MM-DD.md` |
| Pendientes | `Areas/Pendientes.md` |
| Ideas sin repo | `Proyectos/_ideas/<slug>/` |

**Las materias en curso son las que tienen `Wiki/`.**

## Antes de empezar

- La CLI de Obsidian tiene que responder, porque los movimientos se hacen con `obsidian move`. Si no
  responde, pedile al usuario que abra Obsidian. No muevas nada con `mv`.
- Anotá qué archivos de la bóveda ya estaban modificados (`git -C ~/Boveda status --short`). Esos no
  son tuyos.
- Si `Inbox/` está vacía, o sólo tiene un `General.md` vacío, decilo y terminá.

## 1. Notas de clase

Una nota de `Inbox/` que no sea `General.md` es una clase.

1.  **Materia.** Deducila del nombre del archivo (`SO`, `Fisica 2`, `taller`…) y, si hace falta, del
    contenido, comparando con las materias en curso. Si no queda claro, va a la ronda de preguntas.
2.  **Fecha.** Usá la de modificación del archivo. Si la nota menciona otra fecha, usá esa.
3.  **Mover.** Hacelo con `obsidian move` (primero `mkdir -p` de `Clases/`, y la ruta en NFC) al
    nombre `Clase AAAA-MM-DD - <materia>.md`. Si ya existe, agregá ` (2)`.
4.  **Frontmatter.** Agregá `tipo: clase`, `materia: "[[<materia>]]"` y `fecha:`. Además del
    frontmatter, es lo único que se toca de la nota: el texto es del usuario.
5.  **Ingerir.** Aplicá la operación Ingerir de la skill `apuntes` en su modo de cierre: sin preguntar,
    salvo contradicciones, y **sin commitear**. Las dudas que el usuario anotó en clase quedan en el
    resumen de la fuente, respondidas con cita o marcadas como `Abierta`.

## 2. El archivo general

`Inbox/General.md` es texto libre. Partilo en ítems y clasificá cada uno:

| Ítem | Va a |
| :--- | :--- |
| Algo que hizo ("hoy terminé…", "fui a…") | El diario del día, en `Hice` |
| Un pendiente ("tengo que…", "comprar…") | `Areas/Pendientes.md`, sección `Por hacer`, con fecha. Si es de un proyecto, con el enlace a su tarjeta |
| Un link o algo para leer o ver | `Areas/Pendientes.md`, sección `Para leer` |
| Una idea de un proyecto que ya tiene repo | `Areas/Pendientes.md`, sección `Ideas`, con el enlace a la tarjeta. **No** toques su `Estado.md`, que es de `obra`, ni su `Deuda.md`, que es de `tanda` |
| Una idea sin repo | `Proyectos/_ideas/<slug>/<slug>.md` con `tipo: idea`. Si ya existe una parecida, se agrega ahí |
| Una duda o nota de una materia en curso | Se agrega al final de la nota de clase de ese día y esa materia, o se crea una con el ítem, y se ingiere como en el paso 1 |
| Lo que no encaja en ninguna | La ronda de preguntas |

`Areas/Pendientes.md` es una lista de casillas (`- [ ]`). Si no existe, creala con las tres secciones
y `tipo: pendientes`. **No** tachás ni borrás pendientes: eso lo hace el usuario.

## 3. Ronda de preguntas

Juntá todo lo dudoso en **una sola** llamada a `AskUserQuestion`, con hasta 4 preguntas y un destino
concreto propuesto en cada una. Si hay más de 4 dudas, agrupalas.

Pregunta sólo lo que de verdad no se puede deducir:
- la materia de una nota;
- el destino de un ítem ambiguo;
- una contradicción que encontró la ingesta.

## 4. Diario

1.  Mové `Inbox/General.md` a `Areas/Diario/AAAA-MM-DD.md` con `obsidian move`. Así el texto original
    queda guardado tal cual, y la bóveda no borra, archiva.
2.  Arriba del texto agregá frontmatter (`tipo: diario`, `fecha:`) y una sección `## Cierre` con:
    - `Hice`: lo que hizo, en viñetas, con enlaces a los proyectos o materias que menciona;
    - `Clases`: enlaces a las notas de clase del día y a sus resúmenes en la wiki;
    - `Repartido`: qué ítem fue a dónde, en una línea cada uno.
3.  Si la nota del día ya existe, porque el cierre se corrió dos veces, agregá el texto nuevo y
    completá su `## Cierre`, en vez de moverlo.
4.  Creá un `Inbox/General.md` vacío para mañana.

## 5. Resumen y commit

1.  Mostrale al usuario una tabla corta: cada clase con su materia y las páginas de la wiki que tocó,
    y cada ítem del general con su destino.
2.  Hacé un solo commit con las rutas tocadas explícitas, nunca `git add -A`:
    `git -C ~/Boveda commit -m 'cierre: AAAA-MM-DD' -- <rutas>`. Si una de esas rutas ya estaba
    modificada antes de empezar, dejala afuera y avisá.

## Lo que esta skill no hace

- No reescribe lo que escribió el usuario. Sólo lo mueve, le agrega frontmatter o anexa ítems.
- No tacha pendientes ni responde las dudas por fuera de la wiki.
- No toca `Estado.md` ni `Deuda.md` de ningún proyecto.
- No reordena la bóveda. Si algo parece estar en el lugar equivocado, es para `bibliotecario`.
