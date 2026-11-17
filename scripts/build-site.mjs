import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dist = path.join(root, 'dist');
const output = path.join(dist, 'site');
const lock = path.join(dist, '.site-build.lock');
const reserved = new Set(['src', 'scripts', 'tests', 'tools', 'config', 'node_modules', '.git', '.github', 'styles', 'dist']);
let interrupted = false;
for (const [signal, code] of [['SIGINT', 130], ['SIGTERM', 143]]) {
  process.once(signal, () => { interrupted = true; process.exitCode = code; });
}
function checkInterrupted() {
  if (interrupted) throw new Error('Site build interrupted');
}

function relative(name) {
  if (typeof name !== 'string' || !name || /[\\\0:?#]/.test(name)
      || name === '.' || name.endsWith('/') || path.posix.isAbsolute(name) || name.split('/').includes('..')
      || path.posix.normalize(name) !== name) throw new Error(`Unsafe site path: ${name}`);
  return name;
}

async function safeSource(name) {
  let current = root;
  for (const part of relative(name).split('/')) {
    current = path.join(current, part);
    if ((await fs.lstat(current)).isSymbolicLink()) throw new Error(`Site source is a symlink: ${name}`);
  }
  if (!(await fs.stat(current)).isFile()) throw new Error(`Site source is not a file: ${name}`);
  return current;
}

try {
  const stat = await fs.lstat(dist);
  if (stat.isSymbolicLink() || !stat.isDirectory()) throw new Error('Site build directory must be a regular directory');
} catch (error) {
  if (error.code !== 'ENOENT') throw error;
  await fs.mkdir(dist);
}
let acquired = false;
for (let attempt = 0; attempt < 1200; attempt += 1) {
  checkInterrupted();
  try {
    await fs.mkdir(lock);
    acquired = true;
    break;
  } catch (error) {
    if (error.code !== 'EEXIST') throw error;
    if (!(await fs.lstat(lock)).isDirectory() || (await fs.lstat(lock)).isSymbolicLink()) throw new Error('Unsafe site build lock');
    await new Promise(resolve => setTimeout(resolve, 25));
  }
}
if (!acquired) throw new Error('Another site build has not finished; retry after it exits');

let staging;
let previous;
try {
  const configFile = path.join(root, 'config/site-files.json');
  const configBytes = await fs.readFile(configFile);
  const config = JSON.parse(configBytes.toString('utf8'));
  async function checkSources() {
    checkInterrupted();
    if (!(await fs.readFile(configFile)).equals(configBytes)) throw new Error('Site file mapping changed during the build; retry after editing');
    for (const { sourceFile, data } of files.values()) {
      if (!(await fs.readFile(sourceFile)).equals(data)) throw new Error('Site sources changed during the build; retry after editing');
    }
  }
  if (config.schema_version !== 1) throw new Error('Unsupported site-files schema');
  const files = new Map();
  for (const group of ['application', 'downloads']) {
    const entries = config[group];
    if (!entries || typeof entries !== 'object' || Array.isArray(entries)) throw new Error(`Missing site group: ${group}`);
    for (const [source, targetValue] of Object.entries(entries)) {
      const target = relative(targetValue);
      if (reserved.has(target.split('/')[0])) throw new Error(`Developer path cannot be published: ${target}`);
      if (files.has(target)) throw new Error(`Repeated site target: ${target}`);
      const sourceFile = await safeSource(source);
      files.set(target, { sourceFile, data: await fs.readFile(sourceFile) });
    }
  }
  if (!files.has('index.html') || !files.has('sw.js')) throw new Error('Site requires its root HTML and service worker');
  const directories = new Set();
  for (const target of files.keys()) {
    let parent = path.posix.dirname(target);
    while (parent !== '.') {
      directories.add(parent);
      parent = path.posix.dirname(parent);
    }
  }
  let matches = true;
  let found = 0;
  async function compare(directory, prefix = '') {
    for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
      const target = prefix + entry.name;
      if (entry.isSymbolicLink()) throw new Error(`Site output cannot contain symbolic links: ${target}`);
      if (entry.isDirectory()) {
        if (!directories.has(target)) matches = false;
        else await compare(path.join(directory, entry.name), target + '/');
      } else if (!entry.isFile() || !files.has(target)) matches = false;
      else {
        found += 1;
        if (!(await fs.readFile(path.join(directory, entry.name))).equals(files.get(target).data)) matches = false;
      }
    }
  }
  let exists = true;
  try {
    const stat = await fs.lstat(output);
    if (stat.isSymbolicLink() || !stat.isDirectory()) throw new Error('Site output must be a regular directory');
    await compare(output);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    exists = false;
    matches = false;
  }
  await checkSources();
  if (matches && found === files.size) {
    console.log(`Reused ${files.size} unchanged explicitly mapped site files in dist/site`);
  } else {
    staging = await fs.mkdtemp(path.join(dist, '.site-build-'));
    for (const [target, { data }] of files) {
      const destination = path.join(staging, target);
      await fs.mkdir(path.dirname(destination), { recursive: true });
      await fs.writeFile(destination, data);
    }
    await checkSources();
    if (exists) {
      previous = await fs.mkdtemp(path.join(dist, '.site-previous-'));
      await fs.rmdir(previous);
      await fs.rename(output, previous);
    }
    try {
      await fs.rename(staging, output);
      staging = undefined;
    } catch (error) {
      if (previous) {
        await fs.rename(previous, output);
        previous = undefined;
      }
      throw error;
    }
    console.log(`Prepared ${files.size} explicitly mapped site files in dist/site`);
  }
} finally {
  if (staging) await fs.rm(staging, { recursive: true, force: true });
  if (previous) await fs.rm(previous, { recursive: true, force: true });
  await fs.rmdir(lock);
}
