import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

export async function POST() {
  const GITHUB_TOKEN = env.PRIVATE_GITHUB_TOKEN;
  const REPO = 'oracle';
  const OWNER = 'detradefund';
  const WORKFLOW_ID = 'update-balance.yml';
  const BRANCH = 'main';

  if (!GITHUB_TOKEN) {
    return json({ error: 'Token GitHub manquant' }, { status: 500 });
  }

  const res = await fetch(
    `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_ID}/dispatches`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ref: BRANCH })
    }
  );

  if (res.ok) {
    return json({ success: true });
  } else {
    const data = await res.json();
    console.error('GitHub API error:', data);
    return json({ error: data.message || 'Erreur GitHub', details: data }, { status: 500 });
  }
} 