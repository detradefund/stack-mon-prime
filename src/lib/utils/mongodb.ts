import { MongoClient } from 'mongodb';
import type { MongoClientOptions } from 'mongodb';
import { MONGO_URI } from '$env/static/private';

const options: MongoClientOptions = {
  connectTimeoutMS: 10000, // 10 seconds
  socketTimeoutMS: 45000,  // 45 seconds
  serverSelectionTimeoutMS: 10000, // 10 seconds
  maxPoolSize: 10,
  minPoolSize: 1,
  retryWrites: true,
  retryReads: true,
  w: 'majority',
};

// Create a MongoClient with connection pooling
export const createMongoClient = () => {
  return new MongoClient(MONGO_URI, options);
};

// Helper function to get a database connection
export async function withDb<T>(
  dbName: string,
  operation: (db: MongoClient) => Promise<T>
): Promise<T> {
  const client = createMongoClient();
  
  try {
    await client.connect();
    return await operation(client);
  } finally {
    await client.close();
  }
} 