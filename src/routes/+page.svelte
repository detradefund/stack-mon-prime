<script lang="ts">
  import Header from '$lib/components/Header.svelte';
  import Footer from '$lib/components/Footer.svelte';
  import InfoBox from '$lib/components/InfoBox.svelte';
  import OracleBox from '$lib/components/OracleBox.svelte';
  import { wallet } from '$lib/stores/wallet';
  import { fade } from 'svelte/transition';
</script>

<svelte:head>
  <title>Oracle – DeTrade</title>
  <meta name="description" content="Our oracle service ensures transparent valuation events for our vaults, updated every 30 minutes." />
  <meta property="og:title" content="Oracle – DeTrade" />
  <meta property="og:description" content="Our oracle service ensures transparent valuation events for our vaults, updated every 30 minutes" />
  <meta property="og:image" content="https://oracle.detrade.fund/detrade-logo-text.webp" />
  <meta property="og:url" content="https://oracle.detrade.fund" />
  <meta property="og:type" content="website" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
</svelte:head>

<main>
  <Header />
  <div class="content">
    <div class="box-container">
      <InfoBox />
      <OracleBox />
    </div>
    <div class="background-logo"></div>
    <div class="background-wrapper">
      <!-- Autre contenu -->
    </div>
  </div>
  <Footer />

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
</main>

<style>
  main {
    min-height: 100vh;
    background: linear-gradient(135deg, #003366 0%, #001830 85%, #000c1a 100%);
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .background-logo {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 120vh;
    height: 120vh;
    background-image: url('/logo-detrade.png');
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    opacity: 0.01;
    pointer-events: none;
    z-index: 0;
  }

  .background-wrapper {
    position: relative;
    flex: 1;
  }

  .background-wrapper::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at 50% 50%, rgba(77, 168, 255, 0.115) 0%, transparent 54%);
    pointer-events: none;
    animation: pulse 1.5s ease-in-out infinite;
  }

  .content {
    position: relative;
    margin: 0 auto;
    max-width: 1200px;
    padding: 0 2rem;
    z-index: 1;
  }

  h1 {
    color: white;
    font-size: 2.5rem;
    margin-bottom: 2rem;
    text-align: center;
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

  @keyframes pulse {
    0% {
      background: radial-gradient(circle at 50% 50%, rgba(77, 168, 255, 0.11) 0%, transparent 53.5%);
    }
    50% {
      background: radial-gradient(circle at 50% 50%, rgba(77, 168, 255, 0.12) 0%, transparent 54.5%);
    }
    100% {
      background: radial-gradient(circle at 50% 50%, rgba(77, 168, 255, 0.11) 0%, transparent 53.5%);
    }
  }

  @media (max-width: 768px) {
    .box-container {
      margin-top: 120px;
      margin-bottom: 200px;
    }

    .content {
      padding: 0 1rem;
      min-height: calc(100vh - 200px);
    }

    h1 {
      font-size: 2rem;
    }

    .error-toast {
      width: calc(100% - 2rem);
      max-width: none;
      margin: 0 auto;
      bottom: 1rem;
      left: 1rem;
      right: 1rem;
      transform: none;
    }
  }

  .box-container {
    display: flex;
    flex-direction: column;
    gap: 0rem;
    margin-top: 80px;
    position: relative;
    z-index: 2;
  }

  .loading-screen {
    min-height: 100vh;
    background: linear-gradient(135deg, #003366 0%, #001830 85%, #000c1a 100%);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .loading-content {
    color: #94a3b8;
    font-size: 1.125rem;
  }
</style> 