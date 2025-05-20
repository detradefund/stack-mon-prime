import { json } from '@sveltejs/kit';
import type { RequestEvent } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

export async function POST({ request }: RequestEvent) {
  try {
    const { code } = await request.json();

    if (!env.PRIVATE_ADMIN_ACCESS_CODE) {
      return json({ error: 'Configuration manquante' }, { status: 500 });
    }

    if (code === env.PRIVATE_ADMIN_ACCESS_CODE) {
      return json({ success: true });
    } else {
      return json({ error: 'Code incorrect' }, { status: 401 });
    }
  } catch (error) {
    return json({ error: 'Erreur de traitement' }, { status: 500 });
  }
} 