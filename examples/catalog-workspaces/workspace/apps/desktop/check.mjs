import { readFileSync } from 'node:fs';
const content = readFileSync(new URL('./content.txt', import.meta.url), 'utf8');
if (content !== 'Keep this member content unchanged.\n') throw new Error('Content changed');
console.log(JSON.stringify({ member: 'desktop', content: 'unchanged' }));
