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
