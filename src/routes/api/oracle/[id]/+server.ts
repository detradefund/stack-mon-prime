import { json } from '@sveltejs/kit';
import type { RequestEvent } from '@sveltejs/kit';
import { MongoClient } from 'mongodb';
import * as dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Chemin vers le fichier .env dans detrade-core-usdc
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const envPath = join(__dirname, '../../../../../detrade-core-usdc/.env');

// Liste des bases de données valides
const VALID_DATABASES = [
  'detrade-core-usdc',
  'detrade-core-eth'
] as const;

type DatabaseName = typeof VALID_DATABASES[number];

// Vérifier si le fichier .env existe
try {
  dotenv.config({ path: envPath });
  console.log('ENV path:', envPath);
  console.log('ENV loaded:', {
    MONGO_URI: !!process.env.MONGO_URI,
    COLLECTION_NAME: !!process.env.COLLECTION_NAME
  });
} catch (error) {
  console.error('Error loading .env:', error);
}

function isValidDatabase(dbName: string): dbName is DatabaseName {
  return VALID_DATABASES.includes(dbName as DatabaseName);
}

export async function GET({ params, url }: RequestEvent) {
  let client;
  
  try {
    if (!process.env.MONGO_URI || !process.env.COLLECTION_NAME) {
      throw new Error('Missing MongoDB configuration. Please check your .env file.');
    }

    if (!params.id) {
      throw new Error('Database ID is required');
    }

    const databaseName = params.id;
    
    if (!isValidDatabase(databaseName)) {
      throw new Error(`Invalid database name: ${databaseName}. Valid databases are: ${VALID_DATABASES.join(', ')}`);
    }
    
    client = new MongoClient(process.env.MONGO_URI);
    await client.connect();

    const db = client.db(databaseName);
    const collection = db.collection(process.env.COLLECTION_NAME);

    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '5');
    const skip = (page - 1) * limit;
    const vaultId = url.searchParams.get('vaultId');

    // Construire le filtre en fonction de la présence du vaultId
    const filter = vaultId ? { vaultId } : {};

    const [documents, total] = await Promise.all([
      collection.find(filter)
        .sort({ timestamp: -1 })
        .skip(skip)
        .limit(limit)
        .toArray(),
      collection.countDocuments(filter)
    ]);

    return json({
      documents,
      total,
      hasMore: skip + documents.length < total,
      database: databaseName
    });

  } catch (error) {
    console.error('Database error:', error);
    return json({ 
      error: error instanceof Error ? error.message : 'Internal Server Error',
      details: 'Failed to connect to database or retrieve documents'
    }, { status: 500 });
  } finally {
    if (client) {
      await client.close();
    }
  }
} 