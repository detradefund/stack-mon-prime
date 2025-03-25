<script lang="ts">
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import WalletConnect from './WalletConnect.svelte';
    import { wallet } from '$lib/stores/wallet';
    import { fade } from 'svelte/transition';
    import { onDestroy } from 'svelte';
    
    let isScrolled = false;
    let lastScrollY = 0;
    let isLogoHidden = false;
    let errorTimeout: NodeJS.Timeout;
  
    // Modifier la détection du scroll pour être plus robuste sur mobile
    if (typeof window !== 'undefined') {
      const handleScroll = () => {
        isScrolled = window.scrollY > 20;
        isLogoHidden = false; // On garde toujours le logo visible
      };
      
      window.addEventListener('scroll', handleScroll);
      
      onDestroy(() => {
        window.removeEventListener('scroll', handleScroll);
      });
    }
  
    // Vérifier si nous sommes sur une route /app
    $: isAppRoute = true; // On veut toujours afficher le header maintenant
  
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
  
    $: error = $wallet.error;
  </script>
  
  {#if isAppRoute}
  <header class:scrolled={isScrolled}>
    <div class="container">
      <div class="logo-section" class:hidden={isLogoHidden}>
        <img 
          src="/detrade-logo-text.png" 
          alt="DeTrade" 
          class="logo" 
          on:click={() => goto('/')}
        />
      </div>

      <div class="header-right">
        <WalletConnect />
      </div>
    </div>
  </header>
  {/if}
  
  <style>
    header {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      padding: 1.5rem 0;
      transition: all 0.3s ease;
      z-index: 1000;
      background: transparent;
      display: flex;
      justify-content: center;
      border-bottom: 1px solid rgba(255, 255, 255, 0);
    }
  
    .container {
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
      padding-inline: 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: all 0.3s ease;
      position: relative;
    }
  
    header.scrolled {
      background: rgba(13, 17, 28, 0.2);
      backdrop-filter: blur(8px);
      padding: 0.5rem 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
  
    .logo-section {
      display: flex;
      align-items: center;
      transition: all 0.3s ease;
    }
  
    .logo {
      height: 50px;
      cursor: pointer;
      transition: opacity 0.2s ease;
    }
  
    .logo:hover {
      opacity: 0.8;
    }
  
    .wallet-section {
      display: none;
    }
  
    @media (max-width: 768px) {
      header {
        background: rgba(13, 17, 28, 0.2);
        backdrop-filter: blur(8px);
        padding: 1rem 0;
      }
  
      .container {
        padding-inline: 1rem;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
      }
  
      .logo-section {
        margin-bottom: 0.5rem;
        justify-content: center;
        transform: none;
        position: relative;
        z-index: 2;
        opacity: 1;
        height: auto;
        display: flex !important;
      }
  
      .logo {
        height: 32px;
        transform: none;
        display: block;
      }
  
      .logo-section.hidden {
        transform: none;
        opacity: 1;
        margin-bottom: 0.5rem;
        height: auto;
      }
  
      .wallet-section {
        position: relative;
      }
    }
  
    @media (max-width: 480px) {
      .container {
        padding-inline: 0.75rem;
        gap: 0.75rem;
      }
  
      .logo {
        height: 28px;
      }
    }
  
    .header-right {
      display: flex;
      align-items: center;
      gap: 1rem;
      position: relative;
    }
  
    .error-message,
    .error-message a,
    .error-message a:visited,
    .error-message a:hover {
      display: none;
    }
  </style> 