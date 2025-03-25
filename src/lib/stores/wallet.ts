import { writable, derived } from 'svelte/store';
import { NETWORKS, SUPPORTED_CHAIN_IDS } from '$lib/config/networks';
import { resolveEns } from '$lib/utils/ens';
import { logger, LogContext } from '$lib/utils/logger';
import { ethers } from 'ethers';

// Création du store pour le signer
export const signer = writable<ethers.Signer | null>(null);

type WalletState = {
  address: string | null;
  chainId: number | null;
  isConnecting: boolean;
  error: string | null;
  showDisconnectModal: boolean;
  ensName: string | null;
  approveInfinite: boolean;
};

function createWalletStore() {
  logger.info('Initializing wallet store', { context: LogContext.WALLET });
  const { subscribe, set, update } = writable<WalletState>({
    address: null,
    chainId: null,
    isConnecting: false,
    error: null,
    showDisconnectModal: false,
    ensName: null,
    approveInfinite: false
  });

  return {
    subscribe,
    updateEns: async (address: string) => {
      const name = await resolveEns(address);
      update(state => ({ ...state, ensName: name }));
      logger.debug('ENS name updated', { 
        context: LogContext.WALLET,
        data: { address, ensName: name }
      });
    },
    setShowDisconnectModal: (show: boolean) => {
      update(state => ({ ...state, showDisconnectModal: show }));
      logger.debug('Disconnect modal visibility updated', {
        context: LogContext.WALLET,
        data: { show }
      });
    },
    connect: async () => {
      logger.info('Initiating wallet connection', { context: LogContext.WALLET });
      update(state => ({ ...state, isConnecting: true, error: null }));
      
      try {
        // Détection améliorée pour mobile
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        const hasEthereumProvider = Boolean(window.ethereum);
        const hasInjectedProviders = Boolean(window.ethereum?.providers?.length);
        const hasMetaMask = Boolean(window.ethereum?.isMetaMask);
        const hasRabby = Boolean(window.ethereum?.isRabby);

        logger.debug('Environment detection:', {
          context: LogContext.WALLET,
          data: {
            isMobile,
            hasEthereumProvider,
            hasInjectedProviders,
            hasMetaMask,
            hasRabby,
            userAgent: navigator.userAgent
          }
        });

        // Si on est sur mobile, on vérifie si on est dans un wallet browser
        if (isMobile) {
          // Vérifier si on est dans un wallet browser
          const isInWalletBrowser = Boolean(
            window.ethereum?.isMetaMask || 
            window.ethereum?.isRabby ||
            // Autres wallets mobiles courants
            (window as any).ethereum?.isTrust ||
            (window as any).ethereum?.isTokenPocket ||
            (window as any).ethereum?.isCoinbaseWallet ||
            // Vérification générique de provider
            window.ethereum?.request
          );

          if (!isInWalletBrowser) {
            throw new Error('Please open this page in your wallet\'s browser (MetaMask, Rabby, etc.)');
          }
        }

        // Sélection du provider
        let provider = window.ethereum;
        
        if (hasInjectedProviders) {
          const providers = window.ethereum.providers;
          // Priorité : Rabby > MetaMask > Premier provider disponible
          provider = providers.find((p: any) => p.isRabby) || 
                    providers.find((p: any) => p.isMetaMask) || 
                    providers[0];
        }

        if (!provider) {
          throw new Error('No Web3 wallet detected. Please install a wallet like MetaMask or Rabby.');
        }

        // Essayer de se connecter avec le provider sélectionné
        const accounts = await provider.request({ 
          method: 'eth_requestAccounts' 
        }).catch((error: any) => {
          if (error.code === 4001) {
            throw new Error('Please connect your wallet to continue.');
          }
          throw error;
        });

        // Initialiser le provider et le signer
        const ethersProvider = new ethers.providers.Web3Provider(provider, 'any');
        const newSigner = ethersProvider.getSigner();
        signer.set(newSigner);

        logger.debug('Accounts received from wallet', {
          context: LogContext.WALLET,
          data: { accounts }
        });

        const chainId = await provider.request({ 
          method: 'eth_chainId' 
        });

        // Résoudre l'ENS avant de mettre à jour le state
        const ensName = await resolveEns(accounts[0]);

        const newState = {
          address: accounts[0],
          chainId: parseInt(chainId, 16),
          isConnecting: false,
          error: null,
          showDisconnectModal: false,
          ensName: ensName,
          approveInfinite: false
        };
        set(newState);
        logger.info('Wallet connected successfully', {
          context: LogContext.WALLET,
          data: newState
        });
      } catch (error: any) {
        // Si l'erreur est un rejet par l'utilisateur
        if (error?.code === 4001) {
          logger.info('User rejected wallet connection', { 
            context: LogContext.WALLET 
          });
          update(state => ({
            ...state,
            isConnecting: false,
            error: null
          }));
          return;
        }

        const errorMessage = error instanceof Error ? error.message : 
                           typeof error === 'string' ? error :
                           'Failed to connect wallet. Please try again.';

        logger.error('Failed to connect wallet', {
          context: LogContext.WALLET,
          data: { error: errorMessage }
        });
        update(state => ({
          ...state,
          isConnecting: false,
          error: errorMessage
        }));
      }
    },
    disconnect: () => {
      logger.info('Disconnecting wallet', { context: LogContext.WALLET });
      signer.set(null); // Réinitialiser le signer lors de la déconnexion
      const newState = {
        address: null,
        chainId: null,
        isConnecting: false,
        error: null,
        showDisconnectModal: false,
        ensName: null,
        approveInfinite: false
      };
      set(newState);
      logger.info('Wallet disconnected successfully', {
        context: LogContext.WALLET,
        data: newState
      });
    },
    updateChainId: (chainId: number) => {
      logger.info('Updating chain ID', {
        context: LogContext.WALLET,
        data: { chainId }
      });
      update(state => ({ ...state, chainId }));
    },
    updateAddress: async (newAddress: string | undefined) => {
      try {
        if (!newAddress) {
          update(state => ({ 
            ...state, 
            address: null,
            ensName: null
          }));
          return;
        }
        
        logger.debug('Resolving ENS for address', {
          context: LogContext.WALLET,
          data: { address: newAddress }
        });

        // Résoudre l'ENS
        const ensName = await resolveEns(newAddress);
        
        logger.debug('ENS resolution result', {
          context: LogContext.WALLET,
          data: { address: newAddress, ensName }
        });

        // Mettre à jour l'état avec l'adresse et le nom ENS
        update(state => ({ 
          ...state, 
          address: newAddress,
          ensName: ensName || null
        }));
        
      } catch (error) {
        logger.error('Error updating address or resolving ENS', {
          context: LogContext.WALLET,
          data: { 
            address: newAddress,
            error: error instanceof Error ? error.message : String(error)
          }
        });
        
        update(state => ({ 
          ...state, 
          address: null,
          ensName: null
        }));
      }
    },
    reset: () => {
      logger.info('Resetting wallet state', { context: LogContext.WALLET });
      signer.set(null);
      const newState = {
        address: null,
        chainId: null,
        isConnecting: false,
        error: null,
        showDisconnectModal: false,
        ensName: null,
        approveInfinite: false
      };
      set(newState);
      logger.info('Wallet state reset successfully', {
        context: LogContext.WALLET,
        data: newState
      });
    },
    clearError: () => {
      update(state => ({
        ...state,
        error: null
      }));
    }
  };
}

export const wallet = createWalletStore();

// Un seul export pour address, dérivé du store wallet
export const address = derived(wallet, $wallet => $wallet.address);

// MetaMask event listeners
if (typeof window !== 'undefined' && window.ethereum) {
  logger.debug('Setting up MetaMask event listeners', { context: LogContext.WALLET });
  
  window.ethereum.on('accountsChanged', async (accounts: string[]) => {
    logger.info('MetaMask accounts changed', {
      context: LogContext.WALLET,
      data: { accounts }
    });
    if (accounts.length === 0) {
      wallet.disconnect();
    } else {
      await wallet.updateAddress(accounts[0]);
    }
  });

  window.ethereum.on('chainChanged', (chainId: string) => {
    logger.info('MetaMask chain changed', {
      context: LogContext.WALLET,
      data: { chainId, parsed: parseInt(chainId, 16) }
    });
    wallet.updateChainId(parseInt(chainId, 16));
  });

  window.ethereum.on('disconnect', () => {
    logger.info('MetaMask disconnected', { context: LogContext.WALLET });
    wallet.disconnect();
  });
}