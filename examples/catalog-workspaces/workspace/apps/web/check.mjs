import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { name, version } = require('typescript/package.json');
console.log(JSON.stringify({ member: 'web', name, version }));
