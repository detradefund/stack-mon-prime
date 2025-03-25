<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { browser } from '$app/environment';
  import { wallet, signer } from '$lib/stores/wallet';
  import { ethers } from 'ethers';

  // Variables pour le scroll
  let isScrolled = false;
  let lastScrollY = 0;

  // Gestion du scroll
  onMount(() => {
    if (browser) {
      const handleScroll = () => {
        isScrolled = window.scrollY > 20;
        lastScrollY = window.scrollY;
      };

      window.addEventListener('scroll', handleScroll);
      
      checkInitialWalletState();

      return () => {
        window.removeEventListener('scroll', handleScroll);
      };
    }
  });

  async function checkInitialWalletState() {
    if (typeof window !== 'undefined' && window.ethereum) {
      try {
        // Check if already connected
        const accounts = await window.ethereum.request({ 
          method: 'eth_accounts'  // Use eth_accounts to not trigger connect popup
        });
        
        if (accounts.length > 0) {
          const chainId = await window.ethereum.request({ method: 'eth_chainId' });
          const parsedChainId = parseInt(chainId, 16);
          
          // Mettre à jour l'adresse dans tous les cas
          wallet.updateAddress(accounts[0]);
          wallet.updateChainId(parsedChainId);
          
          // Set up provider and signer
          const provider = new ethers.providers.Web3Provider(window.ethereum);
          const newSigner = provider.getSigner();
          signer.set(newSigner);
        }
      } catch (error) {
        console.error('Error checking initial wallet state:', error);
      }
    }
  }
</script>

<svelte:head>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
  <title>DeTrade - Your On-Chain Investment Fund</title>
  <meta name="description" content="Maximize your returns with a secure, transparent, and decentralized vault solution, while maintaining full control over your assets">
</svelte:head>

<div class="website-layout">
  <main>
    <slot />
  </main>
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: #0d111c;
    color: white;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    overflow-x: hidden;
  }

  :global(*) {
    box-sizing: border-box;
  }

  :global(:root) {
    --color-accent: #4DA8FF;
  }

  .website-layout {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }

  main {
    flex: 1;
    width: 100%;
  }
</style> 