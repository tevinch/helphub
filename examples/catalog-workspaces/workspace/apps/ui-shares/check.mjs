import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { name, version } = require('svelte/package.json');
console.log(JSON.stringify({ member: 'ui-shares', name, version }));
