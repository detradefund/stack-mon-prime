<script lang="ts">
  import { fade } from 'svelte/transition';
  import Header from '$lib/components/Header.svelte';
  import Footer from '$lib/components/Footer.svelte';
  
  export let data;

  function formatJson(obj: any) {
    return JSON.stringify(obj, null, 2);
  }
</script>

<svelte:head>
  <title>Document Details - DeTrade</title>
</svelte:head>

<main>
  <Header />
  <div class="content">
    <div class="box-container">
      <div class="wrapper">
        <div class="container">
          <div class="info-box">
            <div class="info-header">
              <h3>Document Details</h3>
            </div>
            <div class="document-content">
              <pre>{formatJson(data.document)}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="background-logo"></div>
    <div class="background-wrapper">
      <!-- Autre contenu -->
    </div>
  </div>
  <Footer />
</main>

<style>
  main {
    min-height: 100vh;
    background: linear-gradient(135deg, #003366 0%, #001830 85%, #000c1a 100%);
    position: relative;
    display: flex;
    flex-direction: column;
  }

  .content {
    position: relative;
    margin: 0 auto;
    max-width: 1200px;
    padding: 0 2rem;
    z-index: 1;
    flex: 1;
  }

  .wrapper {
    width: 100vw;
    background: transparent;
    padding-top: 2rem;
    position: relative;
    left: 50%;
    right: 50%;
    margin-left: -50vw;
    margin-right: -50vw;
  }

  .container {
    max-width: 1200px;
    width: 100%;
    margin: 0 auto;
    padding-inline: 2rem;
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

  .box-container {
    margin-top: 80px;
    margin-bottom: 2rem;
    position: relative;
    z-index: 2;
  }

  .info-box {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 1.5rem;
    width: 100%;
    min-height: 50vh;
    max-height: 70vh;
    height: auto;
    display: flex;
    flex-direction: column;
  }

  .info-header {
    margin-bottom: 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
  }

  .info-header h3 {
    color: #ffffff;
    margin: 0;
    font-size: 1.25rem;
    font-weight: 500;
  }

  .timestamp {
    font-size: 0.875rem;
    color: #64748b;
  }

  .document-content {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    padding: 1.5rem;
    overflow-y: auto;
    flex: 1;
  }

  pre {
    color: #94a3b8;
    margin: 0;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .document-content::-webkit-scrollbar {
    width: 6px;
  }

  .document-content::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 3px;
  }

  .document-content::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
  }

  .document-content::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.15);
  }

  .document-content::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.15);
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
    .content {
      padding: 0 1rem;
    }

    .container {
      padding-inline: 1rem;
    }

    .box-container {
      margin-top: 80px;
      margin-bottom: 80px;
    }

    .info-box {
      min-height: 40vh;
      height: calc(100vh - 300px);
    }

    .info-header {
      justify-content: center;
    }
  }

  @media (max-width: 480px) {
    .container {
      padding-inline: 0.75rem;
    }
  }
</style> 