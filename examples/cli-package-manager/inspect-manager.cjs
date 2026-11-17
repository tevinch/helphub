const fs = require('node:fs');
const path = require('node:path');
const files = ['bun.lock', 'bun.lockb', 'deno.lock', 'pnpm-lock.yaml', 'pnpm-workspace.yaml', 'yarn.lock', 'package-lock.json', 'npm-shrinkwrap.json'];
const known = value => /^(npm|pnpm|yarn|bun|deno)$/.test(value || '') ? value : '(other)';
const field = value => value == null ? '(absent)' : known(typeof value === 'string' ? value.replace(/^\^/, '').split('@')[0] : value.name);
const present = file => { try { return fs.statSync(file).isFile(); } catch { return false; } };
const pnpmOnPath = (process.env.PATH || '').split(path.delimiter).some(dir => {
  const file = path.join(dir || '.', 'pnpm');
  try { fs.accessSync(file, fs.constants.X_OK); return fs.statSync(file).isFile(); } catch { return false; }
});
console.log(JSON.stringify({node: process.version, platform: process.platform, pnpmOnPath,
  launcher: /^(npm|pnpm|yarn|bun|deno)\//.exec(process.env.npm_config_user_agent || '')?.[1] || '(unset/other)'}));
for (let dir = process.cwd(), level = 0; dir !== path.dirname(dir); dir = path.dirname(dir), level++) {
  const matches = files.filter(file => present(path.join(dir, file)));
  let pkg, packageJson = '(absent)';
  if (present(path.join(dir, 'package.json'))) {
    try { pkg = JSON.parse(fs.readFileSync(path.join(dir, 'package.json'), 'utf8')); packageJson = 'readable'; }
    catch { packageJson = 'unreadable/invalid'; }
  }
  if (level === 0 || matches.length || packageJson !== '(absent)') {
    console.log(JSON.stringify({directory: level === 0 ? 'app' : `ancestor ${level}`, files: matches, packageJson,
      packageManager: field(pkg?.packageManager), devEnginesPackageManager: field(pkg?.devEngines?.packageManager)}));
  }
}
