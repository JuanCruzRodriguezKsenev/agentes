# agentes

Fuente única de los agentes y las skills propias que uso en **Claude Code** y en **Antigravity**. Las
copias que leen las herramientas se **generan** desde acá: no se editan a mano.

## Qué hay

```
agentes/<nombre>.md              cuerpo común: marcadores {{...}} y bloques <!-- solo: <plataforma> -->
plataformas/<p>/config.json      dónde se escriben las copias, dónde se enlazan las skills y las reglas, y los marcadores
reglas/<nombre>.md               reglas globales para todos los agentes: se enlazan (clave "reglas" del config.json)
plataformas/<p>/<nombre>.yaml    el frontmatter de ese agente en esa plataforma
skills/<nombre>/SKILL.md         skills propias: se enlazan, no se copian
hooks/proteger-copias            hook de Claude Code que bloquea editar las copias generadas
hooks/regenerar                  hook de Claude Code que corre generar después de editar la fuente
generar                          escribe copias y enlaces; con --check sólo compara
```

## Cambiar algo

1.  Editá `agentes/<nombre>.md`, su `.yaml`, la skill o `reglas/global.md`. Una regla nueva se declara en la
    clave `"reglas"` de cada `config.json` (`"<archivo>": "<ruta del enlace>"`); hoy `global.md` va a
    `~/.claude/rules/global.md` y a `~/.gemini/config/AGENTS.md`.
2.  `~/Dev/agentes/generar`. Desde Claude Code no hace falta: `hooks/regenerar` lo corre solo después de
    cada `Edit`/`Write` en este repo, y si la fuente tiene un error se lo devuelve al modelo. Desde
    Antigravity, o si editás con otra herramienta, corrélo a mano.
3.  Commit y push.

`generar --check` no toca nada y sale con 1 si una copia o un enlace no coincide con la fuente: es la
forma de detectar una copia editada a mano. En Claude Code, además, el hook corta el `Edit`/`Write`
sobre `~/.claude/agents/` y `~/.gemini/config/agents/` antes de que pase.

**Un agente nuevo** lleva `agentes/<nombre>.md` **y** un `.yaml` en cada plataforma; si falta uno,
`generar` se niega a escribir nada. Una copia generada que ya no está en la fuente se borra sola; un
archivo que no lleva el aviso de generado nunca se toca.

## Marcadores y bloques

*   `{{clave}}` se reemplaza por el valor de `marcadores` en el `config.json` de la plataforma, por
    `{{nombre}}` (el del agente) o por una clave del frontmatter del `.md` de la fuente (hoy,
    `descripcion`). Un marcador sin valor es un error.
*   Un párrafo que existe sólo en una plataforma va entre `<!-- solo: claude -->` y `<!-- /solo -->`, en
    líneas propias. El bloque arranca después de una línea en blanco y termina con la suya, así el texto
    queda bien espaciado en las dos salidas.

## Por qué el frontmatter va por plataforma

Porque los dos formatos no son compatibles, y un archivo compartido rompería uno de los dos:

| | Claude Code | Antigravity |
| :--- | :--- | :--- |
| `tools` omitido | hereda todas | `[]`: ninguna |
| `tools` con nombres ajenos | el agente no arranca | — |
| memoria | `memory:` | no existe: va en el cuerpo |
| primer turno | `initialPrompt:` | no existe: sección `# 0. Al arrancar` |
| subagente | lo decide quien delega | `subagent:` (default `true`) |
| `skills` | precarga la skill entera | rutas; entra por nombre y descripción |

La memoria de las dos versiones de un agente es la misma: `.claude/agent-memory/<nombre>/` del proyecto.

## Verificado en Antigravity (agy 1.2.2, 2026-09-12)

*   `agy agents` lista `forja`, `obra` y `tanda`. `verificador` no aparece porque tiene `mainAgent: false`,
    pero sí se puede invocar como subagente.
*   `subagent: false` funciona: `invoke_subagent` sobre `tanda` devuelve `subagent "tanda" not found or not
    allowed to be invoked`.
*   Antigravity sigue el enlace de `~/.gemini/config/skills/spec`, y `skills: - skills/spec` en `tanda`
    resuelve contra `~/.gemini/config/`: `tanda` ve `spec` y ninguna otra skill.
*   `tanda` tiene las herramientas de su `tools` y conoce la ruta de su memoria. `verificador`, como
    subagente, tiene las suyas más `manage_task` y `send_message`, que agrega Antigravity.
*   `permissionMode` no está en la tabla de campos y se sacó de `obra`. El modo de edición lo dan `agentMode`
    en `~/.gemini/antigravity-cli/settings.json` o `agy --mode accept-edits`.

Sigue sin saberse si un subagente puede usar `ask_question`: la documentación sólo habla de pedidos de
autorización que suben al panel principal. Por eso `tanda`, `obra` y `forja` llevan `subagent: false`.

## Fuentes

*   Claude Code: [subagentes](https://code.claude.com/docs/en/sub-agents) ·
    [skills](https://code.claude.com/docs/en/skills) · [hooks](https://code.claude.com/docs/en/hooks)
*   Antigravity: [Subagents](https://antigravity.google/docs/subagents/) ·
    [Introducing Custom Agents](https://antigravity.google/blog/introducing-custom-agents) ·
    [Skills](https://antigravity.google/docs/skills/) · [Rules](https://antigravity.google/docs/rules-workflows/) ·
    [Changelog](https://antigravity.google/changelog?tab=hub) · skill integrada
    `~/.gemini/antigravity-cli/builtin/skills/agy-customizations/`
