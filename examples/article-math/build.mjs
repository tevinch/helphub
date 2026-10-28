import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
export async function buildExample() {
  await build({ absWorkingDir: fileURLToPath(new URL('.', import.meta.url)), entryPoints:['main.jsx'], bundle:true, outdir:'dist', format:'esm',
    define:{'process.env.NODE_ENV':'"production"'}, loader:{'.woff2':'file','.woff':'file','.ttf':'file'}, assetNames:'fonts/[name]-[hash]' });
}
if (process.argv[1] === fileURLToPath(import.meta.url)) await buildExample();

