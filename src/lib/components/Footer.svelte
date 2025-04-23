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
      name: 'Discord',
      url: 'https://discord.gg/AzS9Xd6AM9',
      icon: `<svg xmlns="http://www.w3.org/2000/svg" width="17.6" height="17.6" viewBox="0 0 24 24" fill="currentColor">
        <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/>
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
      url: 'https://docs.detrade.fund'
    },
    {
      name: 'App',
      url: 'https://app.detrade.fund'
    },
    {
      name: 'Website',
      url: 'https://detrade.fund'
    }
  ];
</script>

<footer class="footer">
  <div class="footer-content">
    <div class="social-links">
      {#each socialLinks.filter(link => !link.isImage) as link}
        <a 
          href={link.url}
          target="_blank"
          rel="noopener noreferrer"
          class="social-link"
          aria-label={link.name}
        >
          {@html link.icon}
        </a>
      {/each}
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
        <a href={link.url} target="_blank" rel="noopener noreferrer" class="right-link">
          {link.name}
        </a>
      {/each}
    </div>
  </div>
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
</style> 
