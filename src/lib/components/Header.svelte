<script lang="ts">
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { fade } from 'svelte/transition';
    import { onDestroy, onMount } from 'svelte';
    import { fly } from 'svelte/transition';
    import { quintOut } from 'svelte/easing';
    
    let isHeaderVisible = true;
    let lastScrollY = 0;
    let isMobileMenuOpen = false;
  
    if (typeof window !== 'undefined') {
      const handleScroll = () => {
        const currentScrollY = window.scrollY;
        isHeaderVisible = currentScrollY <= 25 || (currentScrollY < lastScrollY && currentScrollY <= 25);
        lastScrollY = currentScrollY;
      };
      
      window.addEventListener('scroll', handleScroll);
      
      onDestroy(() => {
        if (typeof window !== 'undefined') {
          window.removeEventListener('scroll', handleScroll);
        }
      });
    }
  
    $: isAppRoute = true;

    function scrollToSection(id: string) {
      isMobileMenuOpen = false;
      const section = document.getElementById(id);
      if (section) {
        section.scrollIntoView({ behavior: 'smooth' });
        history.replaceState(null, '', `#${id}`);
      }
    }
</script>
  
{#if isAppRoute}
<header class:hidden={!isHeaderVisible}>
  <div class="header-content">
    <div class="logo-section">
      <img 
        src="/detrade-logo-text.png" 
        alt="DeTrade" 
        class="logo" 
        on:click={() => {
          console.log('[Header] Logo clicked, navigating to home');
          goto('/');
        }}
        role="button"
        tabindex="0"
      />
      <a
        href="https://app2-gules-sigma.vercel.app/"
        class="nav-link desktop"
        target="_blank"
        rel="noopener noreferrer"
        role="button"
        tabindex="0"
      >
        Vaults
      </a>
    </div>
    <div class="header-right">
      <button class="hamburger" on:click={() => isMobileMenuOpen = !isMobileMenuOpen} aria-label="Menu" aria-expanded={isMobileMenuOpen}>
        <span class="bar"></span>
        <span class="bar"></span>
        <span class="bar"></span>
      </button>
    </div>
  </div>
</header>
{/if}
  
{#if isMobileMenuOpen}
  <nav class="mobile-menu" transition:fly={{ y: -40, duration: 600, delay: 900, easing: quintOut }}>
    <a class="nav-link mobile" on:click|preventDefault={() => scrollToSection('vaults')}>Vaults</a>
    <!-- autres liens ici si besoin -->
  </nav>
{/if}
  
<style>
    header {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      width: 100%;
      z-index: 100;
      padding: 1rem 0;
      background: rgba(10, 34, 58, 0.4);
      backdrop-filter: blur(10px);
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      transform: translateY(0);
      box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05);
    }

    header.hidden {
      transform: translateY(-100%);
    }

    .header-content {
      width: 100%;
      max-width: 1800px;
      margin: 0 auto;
      padding: 0 clamp(2.5rem, 10vw, 5rem);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--spacing-lg, 2rem);
      position: relative;
      min-height: 48px;
      height: 48px;
    }
  
    .logo-section {
      display: flex;
      align-items: center;
      gap: 2.5rem;
      padding-left: 0.5rem;
    }
  
    .logo {
      height: clamp(38.8px, 4.8vw, 38.4px);
      width: auto;
      object-fit: contain;
      transition: all 0.3s ease;
      cursor: pointer;
      filter: drop-shadow(0 0 15px rgba(255, 255, 255, 0.3));
    }
  
    .logo:hover {
      opacity: 1;
      transform: scale(1.02);
      filter: drop-shadow(0 0 20px rgba(255, 255, 255, 0.4));
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 1rem;
      position: relative;
    }

    @media (max-width: 1200px) {
      .logo-section {
        gap: 1.5rem;
      }
    }

    @media (max-width: 640px) {
      header {
        padding: 0.75rem 0;
        background: rgba(255, 255, 255, 0.08);
      }
      
      .header-content {
        height: 40px;
        padding: 0 1rem;
      }

      .logo {
        height: 28px;
      }

      .nav-link.desktop {
        display: none;
      }
    }

    .nav-link {
      color: #b4c6ef;
      text-decoration: none;
      font-size: 0.875rem;
      font-weight: 500;
      transition: color 0.2s;
      cursor: pointer;
    }

    .nav-link:hover {
      color: #ffffff;
    }

    .nav-link.desktop {
      display: inline-block;
      font-size: 1rem;
      font-weight: 600;
      color: #ffffff;
      font-family: inherit;
      letter-spacing: inherit;
      position: relative;
      padding: 0.5rem 1.25rem;
      transition: all 0.3s ease;
      background: rgba(10, 34, 58, 0.503);
      border-radius: 0.75rem;
      border: 1px solid rgba(255, 255, 255, 0.05);
      box-shadow: 0 0 0 rgba(25, 62, 182, 0.264);
    }

    .nav-link.desktop:hover {
      color: #ffffff;
      transform: translateY(-2px);
      background: rgba(10, 34, 58, 0.7);
      border-color: rgba(255, 255, 255, 0.1);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    }

    .nav-link.desktop:active {
      transform: translateY(0);
      background: rgba(10, 34, 58, 0.503);
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    }

    /* Menu mobile */
    .hamburger {
      display: none;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      width: 32px;
      height: 32px;
      background: none;
      border: none;
      cursor: pointer;
      z-index: 120;
      margin-left: 0.5rem;
    }

    .hamburger .bar {
      width: 22px;
      height: 3px;
      background: #b4c6ef;
      margin: 3px 0;
      border-radius: 2px;
      transition: all 0.3s;
    }

    @media (max-width: 640px) {
      .hamburger {
        display: flex;
      }
    }

    .mobile-menu {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(13, 25, 42, 0.98);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      z-index: 200;
      gap: 2.5rem;
    }

    .nav-link.mobile {
      font-size: 1.5rem;
      font-weight: 500;
      color: #b4c6ef;
      text-align: center;
      transition: color 0.2s;
    }

    .nav-link.mobile:hover {
      color: #fff;
    }

    @media (min-width: 641px) {
      .mobile-menu {
        display: none;
      }
    }

    .nav-link.desktop.disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .nav-link.desktop.disabled:hover {
      transform: none;
      background: rgba(10, 34, 58, 0.503);
      box-shadow: none;
    }
</style> 