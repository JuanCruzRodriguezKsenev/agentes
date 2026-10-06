# Reglas globales del usuario

Valen para cualquier agente, en cualquier plataforma. Fuente única: `~/Dev/agentes/reglas/global.md`.

## Dónde está el conocimiento

- Lo de `~/Dev` se busca **primero en `~/Boveda`**, la bóveda de Obsidian: la tarjeta de un proyecto es
  `Proyectos/<repo>/<repo>.md`. Si no está ahí, en el repo.
- Las convenciones de la bóveda están en `~/Boveda/AGENTS.md`, y el dueño de su estructura es el agente
  `bibliotecario`. Leelas antes de crear o mover algo ahí.
- Lo que depende del repo se lee de su ficha (`## Mapa de docs`): ahí dice dónde vive el estado, la deuda,
  las specs y los planes. Un repo sin migrar sigue apuntando a su `docs/`; se respeta lo que diga la ficha.

## Qué se queda en el repo (lista cerrada)

- `README.md`, y `AGENTS.md` con su `CLAUDE.md` puntero.
- La referencia del código: arquitectura, schema, testing, security, coding-standards, deployment y contributing.
- El how-to vigente del código.
- ADR y fixtures.

Todo lo demás (estado, deuda, specs, planes, diseños, conocimiento transversal) es trabajo y va a la bóveda.

## Notas de la bóveda

- Frontmatter mínimo: `tipo`, `revisado` (AAAA-MM-DD) y `proyecto` si es de un proyecto.
- Enlaces: wikilink dentro de la bóveda; ruta (`~/Dev/<repo>/…`) entre el repo y la bóveda.
- Mover o renombrar con la CLI de Obsidian, nunca con `mv`.

## Cómo responderle al usuario

- **Bullets, no prosa.** Un bullet por hecho, con su archivo y línea adentro; una o dos líneas cada uno.
- **Pocos:** techo de ~10-12. Pasado eso, lo esencial y ofrecer el resto ("hay N más, te los listo?").
- **Sin secciones `##`** en una respuesta normal: eso es un informe, y sólo si lo pide ("redactá un informe", "ampliá").
- Explicar el contexto **antes** de ofrecer opciones, también en bullets.

## Git

- **No usar SSH para GitHub:** acá falla (`Permission denied (publickey)`). Los remotos van por HTTPS con `gh`
  como gestor de credenciales (`gh auth setup-git`).
- Para crear un repo: `gh repo create <nombre> --private --source=. --remote=origin`, y si el remoto quedó en
  `git@github.com:…`, pasarlo a `https://github.com/…` antes de pushear.
