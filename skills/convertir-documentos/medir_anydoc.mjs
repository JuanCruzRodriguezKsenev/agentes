// Mide anydoc in-process. Lo llama db.py: node medir_anydoc.mjs REP SALIDA ARCHIVO...
// Una línea JSON por archivo. La primera conversión de cada archivo es de calentamiento y no se cuenta.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const dir = path.join(os.homedir(), '.local', 'share', 'convertir-documentos');
const require = createRequire(path.join(dir, 'package.json'));
const anydoc = require('@firecrawl/anydoc');
const { version } = JSON.parse(
  fs.readFileSync(path.join(dir, 'node_modules', '@firecrawl', 'anydoc', 'package.json'), 'utf8'),
);

const [rep, salida, ...archivos] = process.argv.slice(2);
fs.mkdirSync(salida, { recursive: true });

const mediana = (xs) => {
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

for (const [i, archivo] of archivos.entries()) {
  const r = { indice: i + 1, herramienta: 'anydoc', version };
  const tiempos = [];
  let markdown = '';
  for (let n = 0; n <= Number(rep); n++) {
    const t = performance.now();
    try {
      markdown = await anydoc.toMarkdown(archivo);
    } catch (e) {
      tiempos.push(performance.now() - t);
      const code = String(e.code ?? '').toLowerCase();
      r.estado = code.includes('unsupported') ? 'no_soportado' : code.includes('ocr') ? 'necesita_ocr' : 'error';
      r.error = `${e.code ?? ''} ${e.message}`.trim().slice(0, 300);
      markdown = '';
      break;
    }
    if (n > 0) tiempos.push(performance.now() - t);
  }
  r.ms = Math.round(mediana(tiempos) * 10) / 10;
  r.chars = markdown.length;
  if (!r.estado) {
    r.estado = markdown.trim() ? 'ok' : 'vacio';
    r.salida = path.join(salida, `${String(i + 1).padStart(2, '0')}-${path.parse(archivo).name}.anydoc.md`);
    fs.writeFileSync(r.salida, markdown);
  }
  console.log(JSON.stringify(r));
}
