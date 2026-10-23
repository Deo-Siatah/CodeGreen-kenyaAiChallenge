import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function argument(name, fallback) {
  const index = process.argv.indexOf(name);
  if (index === -1) {
    return fallback;
  }
  return process.argv[index + 1] ?? fallback;
}

const farmerId = argument('--farmer', process.env.REPLAY_FARMER_ID);
if (!farmerId) {
  console.error('Usage: npm run record:replay -- --farmer <uuid> [--out <slug>]');
  process.exit(1);
}

const repository = argument('--out', 'grace-wanjiku');
if (!/^[a-z0-9-]+$/.test(repository)) {
  console.error('--out must contain only lowercase letters, digits, and hyphens');
  process.exit(1);
}

const api = argument('--api', process.env.VITE_API_URL || 'http://localhost:8000').replace(
  /\/+$/,
  '',
);
const source = `${api}/api/farmers/${farmerId}/network`;
const response = await fetch(source);

if (!response.ok) {
  console.error(`Recording failed: ${response.status} ${response.statusText}`);
  process.exit(1);
}

const network = await response.json();
const sessionId = network.latest_session?.id;
let breakdown;
if (sessionId) {
  const breakdownResponse = await fetch(`${api}/api/verify/${sessionId}/breakdown`);
  if (breakdownResponse.ok) {
    breakdown = await breakdownResponse.json();
  } else {
    console.warn(
      `Breakdown not recorded: ${breakdownResponse.status} ${breakdownResponse.statusText}`,
    );
  }
}
const recordedAt = new Date().toISOString();
const name =
  typeof network.farmer?.full_name === 'string' ? network.farmer.full_name : 'Recorded case';
const county = typeof network.farmer?.county === 'string' ? ` - ${network.farmer.county}` : '';
const label = argument('--label', `${name}${county}`);
const description = argument(
  '--description',
  `Real backend snapshot recorded on ${recordedAt.slice(0, 10)}.`,
);

const replay = {
  version: 1,
  label,
  description,
  recordedAt,
  source,
  farmer_id: farmerId,
  network,
  ...(breakdown ? { breakdown } : {}),
};

const directory = path.join(root, 'src', 'replay');
const file = path.join(directory, `${repository}.json`);
await mkdir(directory, { recursive: true });
await writeFile(file, `${JSON.stringify(replay, null, 2)}\n`, 'utf8');

console.log(`Wrote ${path.relative(root, file)}`);
console.log(`Recorded ${label} from ${source}`);
