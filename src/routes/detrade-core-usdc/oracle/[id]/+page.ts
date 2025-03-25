import type { PageLoad } from '@sveltejs/kit';

export const load: PageLoad = async ({ params, fetch }) => {
  try {
    const response = await fetch(`/api/oracle/${params.id}`);
    if (!response.ok) throw new Error('Document not found');
    const document = await response.json();
    return { document };
  } catch (error) {
    return {
      status: 404,
      error: 'Document not found'
    };
  }
}; 