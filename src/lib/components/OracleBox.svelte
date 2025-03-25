<script lang="ts">
  import { fade } from 'svelte/transition';
  
  let documents: any[] = [];
  let loading = true;
  let error: string | null = null;
  let currentPage = 1;
  let hasMore = true;
  let initialLoad = true;
  let showError = false;

  async function loadMore() {
    if (loading || !hasMore) return;

    try {
      loading = true;
      const response = await fetch(`/api/oracle?page=${currentPage + 1}&limit=5`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      documents = [...documents, ...data.documents];
      hasMore = data.hasMore;
      currentPage += 1;
    } catch (err) {
      console.error('Error fetching more documents:', err);
      error = 'Failed to load more documents. Please try again later.';
    } finally {
      loading = false;
    }
  }

  function handleScroll(e: Event) {
    const target = e.target as HTMLElement;
    const bottom = target.scrollHeight - target.scrollTop - target.clientHeight < 50;
    
    if (bottom && !loading && hasMore) {
      loadMore();
    }
  }

  async function fetchInitialDocuments() {
    try {
      const response = await fetch(`/api/oracle?page=1&limit=5`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.error) {
        throw new Error(data.error);
      }
      
      documents = data.documents;
      hasMore = data.hasMore;
      error = null;
      showError = false;
    } catch (err) {
      console.error('Error fetching oracle documents:', err);
      error = 'Failed to load documents. Please try again later.';
      documents = [];
      setTimeout(() => {
        showError = true;
      }, 500);
    } finally {
      loading = false;
      initialLoad = false;
    }
  }

  function getTimeAgo(timestamp: string) {
    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return 'just now';
    
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days}d ago`;
    
    const months = Math.floor(days / 30);
    if (months < 12) return `${months}mo ago`;
    
    const years = Math.floor(months / 12);
    return `${years}y ago`;
  }

  function getDocumentLink(doc: any) {
    return `/detrade-core-usdc/oracle/${doc._id}`;
  }

  // Charger les documents au montage du composant
  fetchInitialDocuments();
</script>

<div class="wrapper" in:fade={{ duration: 200 }}>
  <div class="container">
    <div class="info-box">
      <div class="info-header">
        <h3>Oracle Documents</h3>
      </div>
      <div class="info-content" on:scroll={handleScroll}>
        {#if loading && initialLoad}
          <div class="loading">
            <div class="spinner"></div>
          </div>
        {:else if error && showError && !loading}
          <div class="error" transition:fade>{error}</div>
        {:else if documents.length === 0}
          <p>No documents found</p>
        {:else}
          <div class="documents-list">
            {#each documents as doc}
              <div class="document-item">
                <div class="document-header">
                  <div class="left-content">
                    <span class="timestamp">{new Date(doc.timestamp).toLocaleString()}</span>
                    <p class="nav-info">
                      NAV: <span class="nav-value">{doc.nav?.usdc ?? 'N/A'} {doc.nav?.usdc ? 'USDC' : ''}</span>
                    </p>
                  </div>
                  <a 
                    href={getDocumentLink(doc)} 
                    class="time-ago" 
                    target="_blank" 
                    rel="noopener noreferrer"
                  >
                    {getTimeAgo(doc.timestamp)}
                    <svg class="external-link-icon" viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none">
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" stroke-width="2" stroke-linecap="round"/>
                      <path d="M15 3h6v6" stroke-width="2" stroke-linecap="round"/>
                      <path d="M10 14L21 3" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                  </a>
                </div>
              </div>
            {/each}
            {#if loading}
              <div class="loading-more">
                <div class="spinner small"></div>
              </div>
            {/if}
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
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

  .info-box {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 1.5rem;
    width: 100%;
  }

  .info-header {
    margin-bottom: 1rem;
  }

  .info-header h3 {
    color: #ffffff;
    margin: 0;
    font-size: 1.25rem;
    font-weight: 500;
  }

  .info-content {
    color: #94a3b8;
    max-height: 310px;
    overflow-y: auto;
    padding-right: 0.5rem;
  }

  .documents-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .document-item {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    padding: 0.75rem;
    min-height: 70px;
  }

  .document-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 100%;
  }

  .left-content {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .timestamp {
    font-size: 0.875rem;
    color: #64748b;
  }

  .network {
    font-size: 0.875rem;
    color: #38bdf8;
  }

  .document-details {
    font-size: 0.875rem;
  }

  .document-details p {
    margin: 0.25rem 0;
  }

  .loading {
    text-align: center;
    padding: 2rem;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .error {
    color: #ef4444;
    text-align: center;
    padding: 1rem;
  }

  .loading-more {
    text-align: center;
    padding: 0.5rem;
    color: #64748b;
    font-size: 0.875rem;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-radius: 50%;
    border-top-color: #4DA8FF;
    animation: spin 1s ease-in-out infinite;
  }

  .spinner.small {
    width: 20px;
    height: 20px;
    border-width: 2px;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .info-content::-webkit-scrollbar {
    width: 6px;
  }

  .info-content::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 3px;
  }

  .info-content::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
  }

  .info-content::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.15);
  }

  .time-ago {
    font-size: 0.875rem;
    color: #4DA8FF;
    text-decoration: none;
    transition: color 0.2s;
    align-self: center;
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .external-link-icon {
    opacity: 0.8;
    transition: opacity 0.2s;
  }

  .time-ago:hover .external-link-icon {
    opacity: 1;
  }

  @media (max-width: 768px) {
    .wrapper {
      padding-top: 1.5rem;
    }

    .container {
      padding-inline: 1rem;
    }

    .info-box {
      padding: 1rem;
    }

    .info-content {
      max-height: 265px;
    }

    .document-item {
      padding: 0.75rem;
    }
  }

  @media (max-width: 480px) {
    .wrapper {
      padding-top: 1rem;
    }

    .container {
      padding-inline: 0.75rem;
    }
  }

  .nav-info {
    margin: 0;
    font-size: 0.875rem;
    color: #94a3b8;
  }

  .nav-value {
    font-weight: 600;
    background: linear-gradient(135deg, #fff 0%, var(--color-accent) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-fill-color: transparent;
    font-family: 'Roboto Mono', monospace;
  }
</style> 