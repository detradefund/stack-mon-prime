<script lang="ts">
  import Header from '$lib/components/Header.svelte';
  import Footer from '$lib/components/Footer.svelte';
  import FloatingHexagons from '$lib/components/FloatingHexagons.svelte';
  import OracleBox from '$lib/components/OracleBox.svelte';
  import OracleBoxETH from '$lib/components/OracleBoxETH.svelte';
  import InfoBox from '$lib/components/InfoBox.svelte';
  import { wallet } from '$lib/stores/wallet';
  import { fade } from 'svelte/transition';
</script>

<svelte:head>
  <title>DeTrade</title>
  <meta name="description" content="DeTrade - Decentralized Trading Platform" />
  <meta property="og:title" content="DeTrade" />
  <meta property="og:description" content="DeTrade - Decentralized Trading Platform" />
  <meta property="og:image" content="https://oracle.detrade.fund/detrade-logo-text.webp" />
  <meta property="og:url" content="https://oracle.detrade.fund" />
  <meta property="og:type" content="website" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
</svelte:head>

<div class="app">
  <Header />
  <main class="main-content">
    <FloatingHexagons />
    <div class="container">
      <div class="content">
        <InfoBox title="Oracle Overview" />
        <div class="oracle-grid">
          <OracleBox />
          <OracleBoxETH />
        </div>
      </div>
    </div>
  </main>
  <Footer />
</div>

{#if $wallet.error}
  <div class="error-toast" transition:fade={{ duration: 200 }}>
    <p>No Web3 wallet detected. Please install 
      <a 
        href="https://chromewebstore.google.com/detail/rabby-wallet/acmacodkjbdgmoleebolmdjonilkdbch" 
        target="_blank" 
        rel="noopener noreferrer"
      >
        Rabby
      </a>
    </p>
  </div>
{/if}

<style>
  :global(html), :global(body) {
    height: 100%;
    margin: 0;
    padding: 0;
  }

  :global(body) {
    background: linear-gradient(180deg,
      #002F5C 0%,
      #002B51 100%
    );
    color: white;
    background-color: #002B51;
  }

  .app {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  main.main-content {
    flex: 1 0 auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    padding: 2rem 0;
    position: relative;
    z-index: 0;
    width: 100%;
    overflow: hidden;
  }

  :global(footer) {
    flex-shrink: 0;
    width: 100%;
    background: transparent;
  }

  .container {
    width: 100%;
    max-width: 1800px;
    margin: 0 auto;
    padding: 3.5rem clamp(0.75rem, 4.9vw, 4.9rem);
    display: flex;
    flex-direction: column;
    position: relative;
    z-index: 1;
    justify-content: flex-start;
    flex: 1;
    overflow: hidden;
  }

  .content {
    flex: 1;
    overflow: hidden;
    padding: 1rem;
    width: 100%;
  }

  .error-toast {
    position: fixed;
    bottom: 2rem;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(13, 17, 28, 0.95);
    color: var(--color-accent);
    padding: 0 1.5rem;
    height: 42px;
    border-radius: 12px;
    font-size: 0.875rem;
    border: 1px solid rgba(77, 168, 255, 0.2);
    text-align: center;
    backdrop-filter: blur(8px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    white-space: nowrap;
    z-index: 1000;
    max-width: 90%;
    width: fit-content;
  }

  .error-toast a {
    color: var(--color-accent);
    text-decoration: underline;
    font-weight: 500;
    margin-left: 0.25rem;
  }

  .error-toast a:hover {
    text-decoration: none;
  }

  .oracle-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1.5rem;
    width: 100%;
    max-width: 1800px;
    margin: 0 auto;
  }

  @media (max-width: 1024px) {
    .oracle-grid {
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }

    .main-content {
      padding: 1.5rem 0;
    }

    .container {
      padding: 0.75rem;
    }

    .content {
      padding: 0.5rem;
    }
  }

  @media (max-width: 768px) {
    .main-content {
      padding: 1rem 0;
    }

    .container {
      padding: 0.5rem;
    }

    .content {
      padding: 0.25rem;
    }
  }
</style> 