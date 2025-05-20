<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
  import Header from '$lib/components/Header.svelte';
  import Footer from '$lib/components/Footer.svelte';
  import AdminCodeCheck from '$lib/components/AdminCodeCheck.svelte';
  
  let isAuthenticated = false;
  let navStatus = '';
  let navLoading = false;

  onMount(() => {
    if (browser) {
      isAuthenticated = localStorage.getItem('adminAuthenticated') === 'true';
      if (!isAuthenticated) {
        goto('/admin/login');
      }
    }
  });

  async function triggerNAV() {
    navLoading = true;
    navStatus = '';
    try {
      const res = await fetch('/api/admin/trigger-nav', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        navStatus = 'NAV update: workflow triggered successfully!';
      } else {
        navStatus = 'Error: ' + (data.error || 'unknown');
      }
    } catch (e) {
      navStatus = 'Connection error';
    }
    navLoading = false;
  }
</script>

<svelte:head>
  <title>Admin - DeTrade</title>
  <meta name="description" content="Admin dashboard for DeTrade Oracle" />
</svelte:head>

{#if isAuthenticated}
  <main>
    <Header />
    <div class="content">
      <div class="box-container">
        <div class="wrapper">
          <div class="container">
            <div class="info-box">
              <div class="info-header">
                <h3>Admin Dashboard</h3>
                <button class="logout-btn" on:click={() => {
                  localStorage.removeItem('adminAuthenticated');
                  goto('/admin/login');
                }}>
                  Logout
                </button>
              </div>
              <div class="admin-content">
                <p>Welcome to the admin dashboard.</p>
                <div class="nav-action-box">
                  <button class="nav-btn" on:click={triggerNAV} disabled={navLoading}>
                    <svg class="nav-icon" width="20" height="20" fill="none" viewBox="0 0 24 24">
                      <path d="M12 4v16m8-8H4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                    {navLoading ? 'Updating NAV...' : 'Trigger NAV update'}
                  </button>
                  {#if navStatus}
                    <div class="nav-status {navStatus.startsWith('NAV update') ? 'success' : 'error'}">
                      {navStatus}
                    </div>
                  {/if}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="background-logo"></div>
      <div class="background-wrapper">
        <!-- Other content -->
      </div>
    </div>
    <Footer />
  </main>
{:else}
  <AdminCodeCheck />
{/if}

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

  .content {
    position: relative;
    margin: 0 auto;
    max-width: 1200px;
    padding: 0 2rem;
    z-index: 1;
  }

  .box-container {
    display: flex;
    flex-direction: column;
    gap: 0rem;
    margin-top: 80px;
    position: relative;
    z-index: 2;
  }

  .wrapper {
    width: 100%;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .info-box {
    background: rgba(13, 17, 28, 0.2);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 2rem;
    margin-bottom: 2rem;
  }

  .info-header {
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .info-header h3 {
    color: white;
    font-size: 1.5rem;
    margin: 0;
  }

  .admin-content {
    color: #89a6c8;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .nav-action-box {
    background: rgba(13, 17, 28, 0.35);
    border: 1.5px solid rgba(77, 168, 255, 0.15);
    border-radius: 18px;
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15);
    padding: 2.5rem 2rem 2rem 2rem;
    margin-top: 2rem;
    min-width: 340px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .nav-btn {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 1.15rem;
    font-weight: 600;
    background: linear-gradient(90deg, #4da8ff 0%, #1e90ff 100%);
    color: #fff;
    border: none;
    border-radius: 12px;
    padding: 1rem 2.5rem;
    box-shadow: 0 2px 8px rgba(77, 168, 255, 0.15);
    cursor: pointer;
    transition: background 0.2s, transform 0.1s;
    margin-bottom: 1.2rem;
  }
  .nav-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  .nav-btn:hover:not(:disabled) {
    background: linear-gradient(90deg, #1e90ff 0%, #4da8ff 100%);
    transform: translateY(-2px) scale(1.03);
  }
  .nav-icon {
    display: inline-block;
    vertical-align: middle;
  }

  .nav-status {
    font-size: 1rem;
    font-weight: 500;
    padding: 0.5rem 1.2rem;
    border-radius: 8px;
    margin-top: 0.5rem;
    transition: background 0.2s;
    text-align: center;
  }
  .nav-status.success {
    background: rgba(77, 255, 168, 0.12);
    color: #4dffa8;
    border: 1px solid #4dffa8;
  }
  .nav-status.error {
    background: rgba(255, 77, 77, 0.12);
    color: #ff4d4d;
    border: 1px solid #ff4d4d;
  }

  .logout-btn {
    background: transparent;
    border: 1px solid var(--color-accent);
    color: var(--color-accent);
    padding: 0.5rem 1rem;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
  }

  .logout-btn:hover {
    background: var(--color-accent);
    color: white;
  }

  @media (max-width: 768px) {
    .box-container {
      margin-top: 120px;
      margin-bottom: 200px;
    }

    .content {
      padding: 0 1rem;
    }

    .info-box {
      padding: 1.5rem;
    }
    .nav-action-box {
      min-width: unset;
      width: 100%;
      padding: 2rem 0.5rem 1.5rem 0.5rem;
    }
  }
</style> 