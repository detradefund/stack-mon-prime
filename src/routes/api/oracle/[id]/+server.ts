import { json } from '@sveltejs/kit';
import type { RequestEvent } from '@sveltejs/kit';
import { MongoClient, ObjectId } from 'mongodb';
import * as dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const envPath = join(__dirname, '../../../../../detrade-core-usdc/.env');

dotenv.config({ path: envPath });

export async function GET({ params }: RequestEvent) {
  let client;
  
  try {
    if (!process.env.MONGO_URI || !process.env.DATABASE_NAME_1 || !process.env.COLLECTION_NAME) {
      throw new Error('Missing MongoDB configuration');
    }

    client = new MongoClient(process.env.MONGO_URI);
    await client.connect();

    const db = client.db(process.env.DATABASE_NAME_1);
    const collection = db.collection(process.env.COLLECTION_NAME);

    const document = await collection.findOne({ _id: new ObjectId(params.id) });

    if (!document) {
      return json({ error: 'Document not found' }, { status: 404 });
    }

    return json(document);

  } catch (error) {
    console.error('Database error:', error);
    return json({ error: 'Internal Server Error' }, { status: 500 });
  } finally {
    if (client) {
      await client.close();
    }
  }
} 