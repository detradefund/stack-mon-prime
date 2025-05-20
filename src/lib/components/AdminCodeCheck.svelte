<script lang="ts">
  import { fade } from 'svelte/transition';
  import { goto } from '$app/navigation';
  import { browser } from '$app/environment';
  export let lang: 'en' | 'fr' = 'fr';
  
  let code = '';
  let error = '';
  let isChecking = false;
  let blocked = false;
  let cooldownLeft = 0; // en secondes
  
  const MAX_TRIES = 3;
  const COOLDOWN_HOURS = 4;
  const COOLDOWN_MS = COOLDOWN_HOURS * 60 * 60 * 1000;
  
  function t(fr: string, en: string) {
    return lang === 'en' ? en : fr;
  }
  
  function checkBlocked() {
    if (!browser) return;
    const blockedUntil = localStorage.getItem('adminCodeBlockedUntil');
    if (blockedUntil) {
      const until = parseInt(blockedUntil, 10);
      const now = Date.now();
      if (now < until) {
        blocked = true;
        cooldownLeft = Math.ceil((until - now) / 1000);
        return;
      } else {
        // Cooldown terminé, reset
        localStorage.removeItem('adminCodeBlockedUntil');
        localStorage.removeItem('adminCodeTries');
        blocked = false;
        cooldownLeft = 0;
      }
    }
    blocked = false;
    cooldownLeft = 0;
  }
  
  function formatCooldown(sec: number) {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    if (lang === 'en') {
      return `${h}h ${m}m ${s}s`;
    } else {
      return `${h}h ${m}m ${s}s`;
    }
  }
  
  let cooldownInterval: any = null;
  
  function startCooldownTimer() {
    if (cooldownInterval) clearInterval(cooldownInterval);
    cooldownInterval = setInterval(() => {
      checkBlocked();
      if (!blocked && cooldownInterval) {
        clearInterval(cooldownInterval);
      }
    }, 1000);
  }
  
  checkBlocked();
  startCooldownTimer();
  
  async function checkCode() {
    checkBlocked();
    if (blocked) return;
    
    isChecking = true;
    error = '';
    
    try {
      const response = await fetch('/api/admin/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        // Stocker l'authentification dans le localStorage
        localStorage.setItem('adminAuthenticated', 'true');
        localStorage.removeItem('adminCodeTries');
        localStorage.removeItem('adminCodeBlockedUntil');
        // Rediriger vers la page admin
        goto('/admin');
      } else {
        // Gestion des essais
        let tries = parseInt(localStorage.getItem('adminCodeTries') || '0', 10) + 1;
        localStorage.setItem('adminCodeTries', tries.toString());
        if (tries >= MAX_TRIES) {
          const until = Date.now() + COOLDOWN_MS;
          localStorage.setItem('adminCodeBlockedUntil', until.toString());
          checkBlocked();
          startCooldownTimer();
        }
        error = data.error || t('Code incorrect', 'Incorrect code');
        code = '';
      }
    } catch (err) {
      error = t('Erreur de connexion', 'Connection error');
      code = '';
    }
    
    isChecking = false;
  }
</script>

<div class="code-check-container" transition:fade>
  <div class="code-box">
    <h2>{t('Accès Admin', 'Admin Access')}</h2>
    {#if blocked}
      <p class="cooldown">
        {t(
          `Trop de tentatives échouées. Réessayez dans ${formatCooldown(cooldownLeft)}.`,
          `Too many failed attempts. Please try again in ${formatCooldown(cooldownLeft)}.`
        )}
      </p>
    {:else}
      <p>{t("Veuillez entrer le code d'accès", 'Please enter the access code')}</p>
      
      <form on:submit|preventDefault={checkCode}>
        <div class="input-group">
          <input
            type="password"
            bind:value={code}
            placeholder={t('Entrez le code', 'Enter the code')}
            autocomplete="off"
            disabled={blocked}
          />
          <button type="submit" disabled={isChecking || blocked}>
            {isChecking ? t('Vérification...', 'Checking...') : t('Accéder', 'Access')}
          </button>
        </div>
      </form>
      
      {#if error}
        <p class="error" transition:fade>{error}</p>
      {/if}
    {/if}
  </div>
</div>

<style>
  .code-check-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 1rem;
  }
  
  .code-box {
    background: rgba(13, 17, 28, 0.2);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 2rem;
    width: 100%;
    max-width: 400px;
    text-align: center;
  }
  
  h2 {
    color: white;
    margin: 0 0 1rem 0;
    font-size: 1.5rem;
  }
  
  p {
    color: #89a6c8;
    margin: 0 0 1.5rem 0;
  }
  
  .input-group {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }
  
  input {
    flex: 1;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    color: white;
    font-size: 1rem;
  }
  
  input:focus {
    outline: none;
    border-color: var(--color-accent);
  }
  
  button {
    background: var(--color-accent);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  
  button:hover {
    opacity: 0.9;
  }
  
  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .error {
    color: var(--color-error);
    margin: 0;
  }
  
  .cooldown {
    color: #ff4d4d;
    font-weight: 600;
    margin: 1.5rem 0;
  }
</style> 