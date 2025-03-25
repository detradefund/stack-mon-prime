import { ethers } from 'ethers';
import { logger, LogContext } from './logger';
import { env } from '$env/dynamic/public';
import { ensCache } from '$lib/stores/ensCache';
import { get } from 'svelte/store';

declare global {
  interface Window {
    ethereum: any;
  }
}

let provider: ethers.providers.Provider | null = null;

function getProvider(): ethers.providers.Provider {
  if (!provider) {
    // Utiliser Ankr comme provider public
    provider = new ethers.providers.JsonRpcProvider(
      'https://rpc.ankr.com/eth'
    );
  }
  return provider;
}

export async function resolveEns(address: string): Promise<string | null> {
  try {
    // Si l'adresse n'est pas au format hexadécimal, retourner null
    if (!address.startsWith('0x')) {
      return null;
    }
    
    const provider = getProvider();
    // Utiliser lookupAddress pour obtenir le nom ENS d'une adresse
    const ensName = await provider.lookupAddress(address);
    logger.debug('ENS lookup result', {
      context: LogContext.WALLET,
      data: { address, ensName }
    });
    
    return ensName;
  } catch (error) {
    logger.error('ENS resolution failed', {
      context: LogContext.WALLET,
      data: { 
        address,
        error: error instanceof Error ? error.message : String(error)
      }
    });
    return null;
  }
}

export async function resolveAddress(ensName: string): Promise<string | null> {
  try {
    // Vérifier le cache d'abord
    const cachedAddress = ensCache.getReverse(ensName);
    if (cachedAddress !== undefined) {
      logger.debug('Address resolution (from cache)', {
        context: LogContext.WALLET,
        data: { ensName, address: cachedAddress }
      });
      return cachedAddress;
    }

    const provider = getProvider();
    // Si pas dans le cache, faire la requête
    const address = await provider.resolveName(ensName);
    
    // Mettre en cache le résultat (même si null)
    ensCache.setReverse(ensName, address);
    
    return address;
  } catch (error: unknown) {
    logger.error('Address resolution failed', {
      context: LogContext.WALLET,
      data: { error: error instanceof Error ? error.message : String(error) }
    });
    return null;
  }
} 