<script lang="ts">
  import { fade } from 'svelte/transition';
  import { onMount } from 'svelte';
  
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
      console.log('ETH Box - Loading more documents, page:', currentPage + 1);
      loading = true;
      const response = await fetch(`/api/oracle/detrade-core-eth?page=${currentPage + 1}&limit=5`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('ETH Box - Received data:', {
        documentsCount: data.documents?.length,
        total: data.total,
        hasMore: data.hasMore
      });

      documents = [...documents, ...data.documents];
      hasMore = data.hasMore;
      currentPage += 1;
    } catch (err) {
      console.error('ETH Box - Error fetching more documents:', err);
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
      console.log('ETH Box - Fetching initial documents');
      const response = await fetch(`/api/oracle/detrade-core-eth?page=1&limit=5`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('ETH Box - Initial data received:', {
        documentsCount: data.documents?.length,
        total: data.total,
        hasMore: data.hasMore,
        error: data.error
      });

      if (data.error) {
        throw new Error(data.error);
      }
      
      documents = data.documents;
      hasMore = data.hasMore;
      error = null;
      showError = false;
    } catch (err) {
      console.error('ETH Box - Error fetching oracle documents:', err);
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

  function getTimeAgo(timestamp: string | number) {
    if (!timestamp) return 'N/A';
    
    try {
      let date;
      if (typeof timestamp === 'string' && timestamp.includes('UTC')) {
        const [datePart, timePart] = timestamp.split(' UTC')[0].split(' ');
        date = new Date(`${datePart}T${timePart}Z`);
      } else {
        date = new Date(timestamp);
      }

      if (isNaN(date.getTime())) {
        throw new Error('Invalid date');
      }

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
    } catch (e) {
      console.error('Date parsing error:', timestamp, e);
      return 'Invalid date';
    }
  }

  function getDocumentLink(doc: any) {
    return `/detrade-core-eth/oracle/${doc._id}`;
  }

  onMount(() => {
    console.log('ETH Box - Component mounted');
    fetchInitialDocuments();
  });
</script>

<div class="wrapper" in:fade={{ duration: 200 }}>
  <div class="container">
    <div class="info-box">
      <div class="info-header">
        <h3>DeTrade Core ETH</h3>
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
                    <span class="timestamp">
                      {#if doc.timestamp}
                        {(() => {
                          try {
                            const [datePart, timePart] = doc.timestamp.split(' UTC')[0].split(' ');
                            const utcDate = new Date(`${datePart}T${timePart}Z`);
                            
                            if (!isNaN(utcDate.getTime())) {
                              return utcDate.toLocaleString(undefined, {
                                year: 'numeric',
                                month: 'numeric',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                                second: '2-digit'
                              });
                            }
                            return 'Invalid date';
                          } catch (e) {
                            console.error('Erreur parsing date:', e);
                            return 'Invalid date';
                          }
                        })()}
                      {:else}
                        N/A
                      {/if}
                    </span>
                    <p class="nav-info">
                      <span class="nav-label">NAV: </span>
                      <span class="nav-value">
                        {doc.nav?.weth ? Number(doc.nav.weth).toFixed(6) : 'N/A'} {doc.nav?.weth ? 'WETH' : ''}
                      </span>
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
    width: 100%;
    background: transparent;
    padding-top: 0;
    position: relative;
  }

  .container {
    width: 100%;
    margin: 0;
    padding: 0;
  }

  .info-box {
    width: 100%;
    background: rgba(10, 34, 58, 0.503);
    border-radius: 0.75rem;
    box-shadow: 0 0 0 rgba(25, 62, 182, 0.264);
    padding: 2rem;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }

  .info-header {
    margin-bottom: 1.5rem;
    width: 100%;
  }

  .info-header h3 {
    color: #ffffff;
    margin: 0;
    font-size: 1.5rem;
    font-weight: 500;
    background: linear-gradient(135deg, #fff 0%, var(--color-accent) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-fill-color: transparent;
  }

  .info-content {
    color: #94a3b8;
    max-height: calc(55vh - 200px);
    min-height: 300px;
    overflow-y: auto;
    padding-right: 0.5rem;
    width: 100%;
  }

  .documents-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .document-item {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 0.75rem;
    padding: 1rem;
    min-height: 70px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    transition: all 0.2s ease;
  }

  .document-item:hover {
    background: rgba(255, 255, 255, 0.05);
    transform: translateY(-1px);
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
      padding: 1.5rem;
    }

    .info-header h3 {
      font-size: 1.25rem;
    }

    .info-content {
      max-height: 400px;
    }

    .document-item {
      padding: 1rem;
      text-align: center;
    }

    .document-header {
      flex-direction: column;
      gap: 0.5rem;
    }

    .left-content {
      align-items: center;
      gap: 0.4rem;
      width: 100%;
    }

    .timestamp {
      font-size: 0.8rem;
      order: 2;
    }

    .nav-info {
      font-size: 1rem;
      order: 1;
    }

    .nav-info::before {
      content: 'NAV: ';
      display: none;
    }

    .nav-value {
      font-size: 1.1rem;
      display: block;
      margin-top: 0.25rem;
    }

    .time-ago {
      font-size: 0.8rem;
      padding: 0.25rem;
      width: 100%;
      justify-content: center;
      margin-top: 0.25rem;
      opacity: 0.8;
    }

    .time-ago:hover {
      opacity: 1;
    }

    .nav-label {
      display: none;
    }

    .info-header {
      display: flex;
      justify-content: center;
      margin-bottom: 1.5rem;
    }

    .info-header h3 {
      font-size: 1.25rem;
      text-align: center;
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
</style> 