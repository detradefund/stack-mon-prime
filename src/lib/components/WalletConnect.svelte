<script lang="ts">
    import { wallet } from '$lib/stores/wallet';
    import { NETWORKS, type Network } from '$lib/config/networks';
    import { onMount, onDestroy } from 'svelte';
    import { resolveEns } from '$lib/utils/ens';
    import { fade } from 'svelte/transition';
    import { pendingTransaction } from '$lib/stores/pending';
    
    // Default to no network selected if not connected
    $: currentNetwork = $wallet.chainId ? NETWORKS[$wallet.chainId] : null;
    let isNetworkMenuOpen = false;
    let networkDropdown: HTMLDivElement;
    let ensName: string | null = null;
    let errorTimeout: NodeJS.Timeout;
    let isMobile = false;
    // Initialiser showConnectButton en fonction de l'état du wallet
    $: showConnectButton = !$wallet.isConnecting && !$wallet.address;
  
    // Simplifier la logique d'affichage
    $: displayState = $wallet.address ? 'connected' : 
                     $wallet.isConnecting ? 'connecting' : 
                     'disconnected';
  
    function formatAddress(address: string | null): string {
      if (!address) return '';
      return address.length > 10 ? `${address.substring(0, 6)}...${address.substring(address.length - 4)}` : address;
    }
  
    async function handleConnect(targetChainId?: number) {
      try {
        await wallet.connect();
        
        // After connection, get the current network
        if (window.ethereum) {
          const chainId = await window.ethereum.request({ method: 'eth_chainId' });
          const currentChainId = parseInt(chainId, 16);
          
          // Si on a un réseau cible différent du réseau actuel, on switch
          if (targetChainId && targetChainId !== currentChainId) {
            await window.ethereum.request({
              method: 'wallet_switchEthereumChain',
              params: [{ chainId: `0x${targetChainId.toString(16)}` }],
            });
            wallet.updateChainId(targetChainId);
          } else if (NETWORKS[currentChainId]) {
            // Sinon on met à jour avec le réseau actuel s'il est supporté
            wallet.updateChainId(currentChainId);
          }

          // Résoudre l'ENS après la connexion
          const accounts = await window.ethereum.request({ method: 'eth_accounts' });
          if (accounts[0]) {
            const ensName = await resolveEns(accounts[0]);
            if (ensName) {
              wallet.updateEns(ensName);
            }
          }
        }
      } catch (error: any) {
        if (error?.code === 4001) {
          return;
        }
        handleError();
        throw error;
      }
    }
  
    function handleDisconnect() {
      wallet.disconnect();
    }
  
    function handleClickOutside(event: MouseEvent) {
      if (networkDropdown && !networkDropdown.contains(event.target as Node)) {
        isNetworkMenuOpen = false;
      }
    }
  
    // Fonctions de gestion des événements du wallet
    async function handleAccountsChanged(accounts: string[]) {
      if (accounts.length === 0) {
        wallet.disconnect();
      } else {
        wallet.updateAddress(accounts[0]);
        // Résoudre l'ENS pour la nouvelle adresse
        const ensName = await resolveEns(accounts[0]);
        wallet.updateEns(ensName);
      }
    }

    function handleChainChanged(chainId: string) {
      wallet.updateChainId(parseInt(chainId, 16));
    }
  
    onMount(() => {
      document.addEventListener('click', handleClickOutside);
      // Vérifier si un provider Ethereum est disponible
      if (window.ethereum?.providers) {
        const provider = window.ethereum.providers.find((p: any) => p.isRabby) || window.ethereum.providers[0];
        provider.on('accountsChanged', handleAccountsChanged);
        provider.on('chainChanged', handleChainChanged);
        provider.on('disconnect', handleDisconnect);
      } else if (window.ethereum) {
        window.ethereum.on('accountsChanged', handleAccountsChanged);
        window.ethereum.on('chainChanged', handleChainChanged);
        window.ethereum.on('disconnect', handleDisconnect);
      }

      // Vérifier si on est sur mobile
      const checkMobile = () => {
        isMobile = window.innerWidth <= 768;
      };
      
      checkMobile();
      window.addEventListener('resize', checkMobile);

      return () => {
        document.removeEventListener('click', handleClickOutside);
        if (window.ethereum?.providers) {
          const provider = window.ethereum.providers.find((p: any) => p.isRabby) || window.ethereum.providers[0];
          provider.removeListener('accountsChanged', handleAccountsChanged);
          provider.removeListener('chainChanged', handleChainChanged);
          provider.removeListener('disconnect', handleDisconnect);
        } else if (window.ethereum) {
          window.ethereum.removeListener('accountsChanged', handleAccountsChanged);
          window.ethereum.removeListener('chainChanged', handleChainChanged);
          window.ethereum.removeListener('disconnect', handleDisconnect);
        }
        window.removeEventListener('resize', checkMobile);
      };
    });
  
    async function handleNetworkSwitch(chainId: number) {
      try {
        if (!$wallet.address) {
          // If not connected, connect first with the target network
          await handleConnect(chainId);
          isNetworkMenuOpen = false;
          return;
        }
        
        // Si nous avons plusieurs providers, essayer de trouver le bon
        let provider = window.ethereum;
        if (window.ethereum?.providers) {
          provider = window.ethereum.providers.find((p: any) => p.isRabby) || window.ethereum.providers[0];
        }

        if (provider) {
          await provider.request({
            method: 'wallet_switchEthereumChain',
            params: [{ chainId: `0x${chainId.toString(16)}` }],
          });
          isNetworkMenuOpen = false;
        }
      } catch (error: any) {
        // Si l'erreur est un rejet par l'utilisateur, on ne fait rien
        if (error?.code === 4001) {
          return;
        }
        // Pour les autres erreurs, on log mais sans afficher d'erreur à l'utilisateur
        console.error('Network switch failed:', error);
      }
    }

    // Fonction pour gérer le timeout du message d'erreur
    function handleError() {
      if (errorTimeout) clearTimeout(errorTimeout);
      if ($wallet.error) {
        errorTimeout = setTimeout(() => {
          wallet.clearError();
        }, 10000);
      }
    }

    // Observer les changements d'erreur
    $: if ($wallet.error !== null) handleError();

    onDestroy(() => {
      if (errorTimeout) clearTimeout(errorTimeout);
    });

    export let error = $wallet.error; // Expose l'erreur
  </script>
  
  <div class="wallet-section">
    <div class="wallet-content">
      {#if $wallet.address}
        <div 
          class="network dropdown"
          class:open={isNetworkMenuOpen}
          bind:this={networkDropdown}
          on:click|stopPropagation={() => isNetworkMenuOpen = !isNetworkMenuOpen}
        >
          <div class="network-content">
            {#if currentNetwork}
              <div class="network-info">
                <img src={currentNetwork.icon} alt={currentNetwork.name} />
                <span>{currentNetwork.name}</span>
              </div>
            {:else}
              <div class="network-info">
                <span>Select Network</span>
              </div>
            {/if}
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              width="16" 
              height="16" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              stroke-width="2" 
              stroke-linecap="round" 
              stroke-linejoin="round"
              class="chevron"
              class:open={isNetworkMenuOpen}
            >
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
          <div class="dropdown-content" class:show={isNetworkMenuOpen}>
            {#each Object.values(NETWORKS).filter(network => network.id !== $wallet.chainId) as network}
              <button 
                class="network-option" 
                on:click|stopPropagation={() => handleNetworkSwitch(network.id)}
              >
                <div class="network-info">
                  <img src={network.icon} alt={network.name} />
                  <span>{network.name}</span>
                </div>
              </button>
            {/each}
          </div>
        </div>
        
        <button class="connect-btn connected" on:click={() => wallet.setShowDisconnectModal(true)}>
          {#if $pendingTransaction.isTransactionPending}
            <div class="transaction-status">
              <svg class="pulse-ring" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" />
              </svg>
              <span>Pending...</span>
            </div>
          {:else}
            {#if $wallet.ensName}
              {$wallet.ensName}
            {:else}
              {formatAddress($wallet.address)}
            {/if}
          {/if}
        </button>
      {:else}
        <button 
          class="connect-btn"
          on:click={() => handleConnect()}
          disabled={$wallet.isConnecting}
        >
          {$wallet.isConnecting ? 'Connecting...' : 'Connect Wallet'}
        </button>
      {/if}
    </div>
  </div>
  
  {#if $wallet.showDisconnectModal}
    <div class="modal-overlay" on:click={() => wallet.setShowDisconnectModal(false)}>
      <div class="modal" on:click|stopPropagation>
        <h3>Disconnect Wallet</h3>
        <p>Are you sure you want to disconnect your wallet?</p>
        <div class="modal-actions">
          <button class="cancel-btn" on:click={() => wallet.setShowDisconnectModal(false)}>
            Cancel
          </button>
          <button 
            class="disconnect-btn" 
            on:click={() => {
              handleDisconnect();
              wallet.setShowDisconnectModal(false);
            }}
          >
            Disconnect
          </button>
        </div>
      </div>
    </div>
  {/if}
  
  <style>
    .wallet-section {
      display: flex;
      align-items: center;
      gap: 1rem;
      position: relative;
      justify-content: flex-end;
    }
  
    .wallet-content {
      display: flex;
      align-items: center;
      gap: 1rem;
      justify-content: flex-end;
    }
  
    .network {
      display: flex;
      flex-direction: column;
      background: rgba(13, 17, 28, 0.2);
      border-radius: 12px;
      border: 1px solid rgba(77, 168, 255, 0.2);
      width: 180px;
      position: relative;
      transition: all 0.2s ease;
    }
  
    .network:hover, .network.open {
      border-color: rgba(77, 168, 255, 0.4);
      background: rgba(13, 17, 28, 0.3);
    }
  
    .network-content {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 1rem;
      cursor: pointer;
      height: 40px;
      box-sizing: border-box;
    }
  
    .network-info {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin: 0 auto; /* Centre le bloc */
    }
  
    .network img {
      width: 20px;
      height: 20px;
    }
  
    .network span {
      color: #60a5fa;
      font-size: 0.9rem;
      font-weight: 500;
    }
  
    .chevron {
      color: #60a5fa;
      transition: transform 0.2s ease;
      width: 14px;
      height: 14px;
    }
  
    .chevron.open {
      transform: rotate(180deg);
    }
  
    .connect-btn {
      height: 42px;
      width: 180px;
      padding: 0 1rem;
      font-size: 1rem;
      font-weight: 600;
      color: #0d111c;
      background: linear-gradient(135deg, #fff 0%, var(--color-accent) 100%);
      border: none;
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.3s ease;
      box-shadow: 
        0 4px 15px rgba(77, 168, 255, 0.3),
        0 0 25px rgba(77, 168, 255, 0.5),
        0 0 45px rgba(77, 168, 255, 0.3);
      position: relative;
      animation: buttonGlow 2s ease-in-out infinite;
      white-space: nowrap;
      text-align: center;
    }
  
    .connect-btn::before {
      content: '';
      position: absolute;
      top: -3px;
      left: -3px;
      right: -3px;
      bottom: -3px;
      background: radial-gradient(circle at 50% 50%, rgba(77, 168, 255, 0.2) 0%, transparent 70%);
      border-radius: 8px;
      filter: blur(6px);
      z-index: -1;
      animation: buttonPulse 2s ease-in-out infinite;
    }
  
    @keyframes buttonGlow {
      0%, 100% {
        box-shadow: 
          0 4px 15px rgba(77, 168, 255, 0.3),
          0 0 25px rgba(77, 168, 255, 0.4),
          0 0 45px rgba(77, 168, 255, 0.2);
      }
      50% {
        box-shadow: 
          0 4px 15px rgba(77, 168, 255, 0.35),
          0 0 28px rgba(77, 168, 255, 0.45),
          0 0 48px rgba(77, 168, 255, 0.25);
      }
    }
  
    @keyframes buttonPulse {
      0%, 100% {
        opacity: 0.85;
        transform: scale(1);
      }
      50% {
        opacity: 1;
        transform: scale(1.02);
      }
    }
  
    .connect-btn:hover {
      transform: translateY(-2px);
      box-shadow: 
        0 6px 20px rgba(77, 168, 255, 0.4),
        0 0 30px rgba(77, 168, 255, 0.6),
        0 0 50px rgba(77, 168, 255, 0.4);
    }
  
    .connect-btn:active {
      transform: translateY(0);
      box-shadow: 
        0 4px 15px rgba(77, 168, 255, 0.2),
        0 0 20px rgba(77, 168, 255, 0.4),
        0 0 40px rgba(77, 168, 255, 0.2);
    }
  
    .connect-btn.connected {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(77, 168, 255, 0.2) 100%);
      color: var(--color-accent);
      border: 1px solid var(--color-accent);
      width: 180px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      box-shadow: none;
      animation: none;
    }
  
    .connect-btn.connected:hover {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(77, 168, 255, 0.25) 100%);
      transform: none;
      box-shadow: none;
    }
  
    .connect-btn.connected:active {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(77, 168, 255, 0.15) 100%);
      transform: none;
      box-shadow: none;
    }
  
    .dropdown {
      position: relative;
      cursor: pointer;
    }
  
    .dropdown-content {
      position: absolute;
      top: 100%;
      left: -1px;
      right: -1px;
      background: rgba(13, 17, 28, 0.3);
      border: 1px solid rgba(77, 168, 255, 0.4);
      border-bottom-left-radius: 12px;
      border-bottom-right-radius: 12px;
      display: none;
      flex-direction: column;
      overflow: hidden;
      z-index: 1000;
      padding: 0.25rem;
      margin-top: -1px;
      border-top: 0;
    }
  
    .network.open {
      border-bottom-left-radius: 0;
      border-bottom-right-radius: 0;
      border-bottom: 0;
    }
  
    .dropdown-content.show {
      display: flex;
      animation: dropdownSlide 0.2s ease;
    }
  
    @keyframes dropdownSlide {
      from {
        opacity: 0;
        transform: translateY(-8px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
  
    .network-option {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      padding: 0.75rem 1rem;
      background: transparent;
      border: none;
      color: #60a5fa;
      cursor: pointer;
      transition: all 0.15s ease;
      border-radius: 8px;
      box-sizing: border-box;
      height: 40px;
    }
  
    .network-option .network-info {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin: 0 auto;
    }
  
    .network-option:hover {
      background: rgba(77, 168, 255, 0.1);
    }
  
    .network-option img {
      width: 20px;
      height: 20px;
    }
  
    .network-option.active {
      background: rgba(77, 168, 255, 0.15);
      color: #60a5fa;
      font-weight: 500;
    }
  
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }
  
    .modal {
      background: rgba(13, 17, 28, 0.95);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 1.5rem;
      width: 90%;
      max-width: 400px;
    }
  
    .modal h3 {
      color: white;
      margin: 0 0 1rem;
    }
  
    .modal p {
      color: #94a3b8;
      margin: 0 0 1.5rem;
    }
  
    .modal-actions {
      display: flex;
      gap: 1rem;
      justify-content: flex-end;
    }
  
    .cancel-btn,
    .disconnect-btn {
      padding: 0.5rem 1rem;
      border-radius: 8px;
      font-size: 0.875rem;
      cursor: pointer;
      transition: all 0.2s ease;
    }
  
    .cancel-btn {
      background: none;
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #94a3b8;
    }
  
    .disconnect-btn {
      background: rgba(77, 168, 255, 0.1);
      border: 1px solid var(--color-accent);
      color: var(--color-accent);
    }
  
    .wallet-address {
      color: var(--color-accent);
    }
  
    .loading-spinner {
      width: 16px;
      height: 16px;
      border: 2px solid rgba(96, 165, 250, 0.2);
      border-top-color: var(--color-accent);
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-right: 8px;
      display: inline-block;
    }
  
    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }
  
    .transaction-text {
      font-size: 0.875rem;
      color: var(--color-accent);
    }
  
    .transaction-status {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--color-accent);
      font-weight: 500;
    }
  
    .pulse-ring {
      width: 14px;
      height: 14px;
      animation: pulse 1.5s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }
  
    .pulse-ring circle {
      fill: none;
      stroke: var(--color-accent);
      stroke-width: 2;
      stroke-dasharray: 70;
      stroke-dashoffset: 20;
      stroke-linecap: round;
    }
  
    @keyframes pulse {
      0% {
        transform: rotate(0deg);
        opacity: 1;
      }
      50% {
        opacity: 0.5;
      }
      100% {
        transform: rotate(360deg);
        opacity: 1;
      }
    }
  </style> 