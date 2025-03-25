<script>
  import { fade } from 'svelte/transition';
  
  const socialLinks = [
    {
      name: 'X',
      url: 'https://x.com/detradefund',
      icon: `<svg xmlns="http://www.w3.org/2000/svg" width="17.6" height="17.6" viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
      </svg>`
    },
    {
      name: 'Powered by Lagoon',
      url: 'https://lagoon.finance',
      isImage: true,
      imageSrc: '/white_horizontal_powered_by_lagoon.svg'
    }
  ];

  const rightLinks = [
    {
      name: 'Documentation',
      comingSoon: true
    },
    {
      name: 'Website',
      url: 'https://detrade.fund'
    }
  ];

  let showComingSoon = false;
  let comingSoonTimeout;

  function handleDocClick(e) {
    e.preventDefault();
    showComingSoon = true;
    
    // Clear any existing timeout
    if (comingSoonTimeout) clearTimeout(comingSoonTimeout);
    
    // Hide the message after 2 seconds
    comingSoonTimeout = setTimeout(() => {
      showComingSoon = false;
    }, 2000);
  }
</script>

<footer class="footer">
  <div class="footer-content">
    <div class="social-links">
      <a 
        href="https://x.com/detradefund"
        target="_blank"
        rel="noopener noreferrer"
        class="social-link"
        aria-label="X"
      >
        {@html socialLinks[0].icon}
      </a>
    </div>

    <div class="lagoon-container">
      <a 
        href="https://lagoon.finance"
        target="_blank"
        rel="noopener noreferrer"
        class="lagoon-link"
        aria-label="Powered by Lagoon"
      >
        <img src="/white_horizontal_powered_by_lagoon.svg" alt="Powered by Lagoon" class="lagoon-logo" />
      </a>
    </div>

    <div class="right-links">
      {#each rightLinks as link}
        {#if link.comingSoon}
          <div class="link-wrapper">
            <button class="right-link coming-soon-btn" on:click={handleDocClick}>
              {link.name}
            </button>
            <span class="coming-soon-badge">Coming soon</span>
          </div>
        {:else}
          <a href={link.url} target="_blank" rel="noopener noreferrer" class="right-link">
            {link.name}
          </a>
        {/if}
      {/each}
    </div>
  </div>

  {#if showComingSoon}
    <div class="coming-soon-tooltip" transition:fade>
      Coming soon
    </div>
  {/if}
</footer>

<style>
  .footer {
    width: 100%;
    padding: 1.65rem 0;
    margin-top: auto;
    position: absolute;
    bottom: 0;
    left: 0;
    background: transparent;
  }

  .footer-content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: relative;
  }

  .social-links {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .social-link {
    color: #94a3b8;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.55rem;
    border-radius: 8px;
    text-decoration: none;
  }

  .social-link:hover {
    color: #60a5fa;
    background: rgba(96, 165, 250, 0.05);
    transform: translateY(-1px);
  }

  .right-links {
    display: flex;
    gap: 1.5rem;
    align-items: flex-start;
  }

  .right-link {
    color: #94a3b8;
    text-decoration: none;
    font-size: 0.96rem;
    transition: all 0.2s ease;
    position: relative;
  }

  .right-link:hover {
    color: #60a5fa;
    transform: translateY(-1px);
  }

  .lagoon-container {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
  }

  .lagoon-link {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.55rem;
    border-radius: 8px;
    transition: all 0.2s ease;
  }

  .lagoon-link:hover {
    background: rgba(96, 165, 250, 0.05);
    transform: translateY(-1px);
  }

  .lagoon-logo {
    height: 17.6px;
    width: auto;
    filter: brightness(0) saturate(100%) invert(71%) sepia(9%) saturate(342%) hue-rotate(179deg) brightness(89%) contrast(84%);
    transition: all 0.2s ease;
  }

  .lagoon-link:hover .lagoon-logo {
    filter: brightness(0) saturate(100%) invert(67%) sepia(69%) saturate(1302%) hue-rotate(185deg) brightness(101%) contrast(96%);
  }

  @media (max-width: 768px) {
    .footer-content {
      flex-direction: column;
      gap: 1.5rem;
      padding: 0 1rem;
    }

    .lagoon-container {
      position: static;
      transform: none;
      order: 2;
    }

    .social-links {
      order: 1;
    }

    .right-links {
      order: 3;
    }
  }

  .coming-soon-btn {
    background: none;
    border: none;
    padding: 0;
    font: inherit;
    cursor: pointer;
  }

  .coming-soon-tooltip {
    position: absolute;
    bottom: calc(100% + 10px);
    left: 50%;
    transform: translateX(-50%);
    background: rgba(13, 17, 28, 0.95);
    border: 1px solid var(--color-accent);
    color: var(--color-accent);
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-size: 0.875rem;
    white-space: nowrap;
    pointer-events: none;
  }

  /* Make the coming soon button look like other links */
  .coming-soon-btn {
    color: #94a3b8;
    text-decoration: none;
    font-size: 0.96rem;
    transition: all 0.2s ease;
  }

  .coming-soon-btn:hover {
    color: #60a5fa;
    transform: translateY(-1px);
  }

  .link-wrapper {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }

  .coming-soon-badge {
    font-size: 0.75rem;
    color: #60a5fa;
    font-style: italic;
    opacity: 0.8;
    line-height: 1;
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    margin-top: 0.25rem;
    text-align: center;
    width: 100%;
  }
</style> 
