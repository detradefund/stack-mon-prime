import { writable, get } from 'svelte/store';
import { logger, LogContext } from '$lib/utils/logger';

interface ENSCacheEntry {
  value: string | null;
  timestamp: number;
}

interface ENSCacheStore {
  forward: { [address: string]: ENSCacheEntry }; // address -> ENS
  reverse: { [ens: string]: ENSCacheEntry };     // ENS -> address
}

// Cache durée de vie en millisecondes (1 heure)
const CACHE_TTL = 3600000;
const STORAGE_KEY = 'ens_cache';

// Fonction pour charger le cache depuis localStorage
function loadFromStorage(): ENSCacheStore {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Nettoyer les entrées expirées au chargement
      const now = Date.now();
      Object.entries(parsed.forward).forEach(([key, entry]: [string, ENSCacheEntry]) => {
        if (now - entry.timestamp > CACHE_TTL) {
          delete parsed.forward[key];
        }
      });
      Object.entries(parsed.reverse).forEach(([key, entry]: [string, ENSCacheEntry]) => {
        if (now - entry.timestamp > CACHE_TTL) {
          delete parsed.reverse[key];
        }
      });
      return parsed;
    }
  } catch (error) {
    logger.error('Failed to load ENS cache from storage', {
      context: LogContext.WALLET,
      data: { error }
    });
  }
  return { forward: {}, reverse: {} };
}

function createENSCache() {
  // Initialiser avec les données du localStorage
  const { subscribe, set, update } = writable<ENSCacheStore>(
    typeof window !== 'undefined' ? loadFromStorage() : { forward: {}, reverse: {} }
  );

  function saveToStorage(store: ENSCacheStore) {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
      } catch (error) {
        logger.error('Failed to save ENS cache to storage', {
          context: LogContext.WALLET,
          data: { error }
        });
      }
    }
  }

  return {
    subscribe,

    // Ajouter ou mettre à jour une entrée address -> ENS
    setForward: (address: string, ensName: string | null) => {
      update(store => {
        const newStore = {
          ...store,
          forward: {
            ...store.forward,
            [address.toLowerCase()]: {
              value: ensName,
              timestamp: Date.now()
            }
          }
        };
        saveToStorage(newStore);
        return newStore;
      });
      
      logger.debug('ENS cache updated (forward)', {
        context: LogContext.WALLET,
        data: { address, ensName }
      });
    },

    // Ajouter ou mettre à jour une entrée ENS -> address
    setReverse: (ensName: string, address: string | null) => {
      update(store => {
        const newStore = {
          ...store,
          reverse: {
            ...store.reverse,
            [ensName.toLowerCase()]: {
              value: address,
              timestamp: Date.now()
            }
          }
        };
        saveToStorage(newStore);
        return newStore;
      });
      
      logger.debug('ENS cache updated (reverse)', {
        context: LogContext.WALLET,
        data: { ensName, address }
      });
    },

    // Récupérer une entrée du cache address -> ENS
    getForward: (address: string): string | null | undefined => {
      let entry = get(ensCache).forward[address.toLowerCase()];
      
      if (!entry) return undefined;
      
      // Vérifier si l'entrée n'est pas expirée
      if (Date.now() - entry.timestamp > CACHE_TTL) {
        logger.debug('ENS cache entry expired (forward)', {
          context: LogContext.WALLET,
          data: { address }
        });
        return undefined;
      }
      
      return entry.value;
    },

    // Récupérer une entrée du cache ENS -> address
    getReverse: (ensName: string): string | null | undefined => {
      let entry = get(ensCache).reverse[ensName.toLowerCase()];
      
      if (!entry) return undefined;
      
      // Vérifier si l'entrée n'est pas expirée
      if (Date.now() - entry.timestamp > CACHE_TTL) {
        logger.debug('ENS cache entry expired (reverse)', {
          context: LogContext.WALLET,
          data: { ensName }
        });
        return undefined;
      }
      
      return entry.value;
    },

    // Nettoyer les entrées expirées
    cleanup: () => {
      const now = Date.now();
      
      update(store => {
        const newStore = {
          forward: { ...store.forward },
          reverse: { ...store.reverse }
        };

        // Nettoyer le cache forward
        Object.entries(newStore.forward).forEach(([address, entry]) => {
          if (now - entry.timestamp > CACHE_TTL) {
            delete newStore.forward[address];
          }
        });
        
        // Nettoyer le cache reverse
        Object.entries(newStore.reverse).forEach(([ensName, entry]) => {
          if (now - entry.timestamp > CACHE_TTL) {
            delete newStore.reverse[ensName];
          }
        });
        
        saveToStorage(newStore);
        return newStore;
      });
      
      logger.debug('ENS cache cleanup performed', {
        context: LogContext.WALLET
      });
    },

    // Vider complètement le cache
    clear: () => {
      if (typeof window !== 'undefined') {
        localStorage.removeItem(STORAGE_KEY);
      }
      set({ forward: {}, reverse: {} });
      
      logger.debug('ENS cache cleared', {
        context: LogContext.WALLET
      });
    }
  };
}

export const ensCache = createENSCache();

// Nettoyer le cache toutes les heures
if (typeof window !== 'undefined') {
  setInterval(() => {
    ensCache.cleanup();
  }, CACHE_TTL);
} 