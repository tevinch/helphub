import { transformFileAsync } from '@babel/core';
import { build } from 'esbuild';
import { mkdir, writeFile, copyFile } from 'node:fs/promises';

await mkdir('dist', { recursive: true });
const result = await transformFileAsync('src/main.tsx', {
  babelrc: false,
  configFile: false,
  plugins: [['@solidjs/babel-plugin', { generate: 'dom' }]],
  presets: ['@babel/preset-typescript'],
});
if (!result?.code) throw new Error('The Solid compiler returned no output');
await writeFile('dist/compiled.js', result.code);
await build({
  stdin: { contents: result.code, resolveDir: process.cwd(), sourcefile: 'main.js' },
  outfile: 'dist/main.js', bundle: true, format: 'esm', platform: 'browser',
  target: 'es2022', define: { 'process.env.NODE_ENV': '"production"' },
});
await copyFile('index.html', 'dist/index.html');
