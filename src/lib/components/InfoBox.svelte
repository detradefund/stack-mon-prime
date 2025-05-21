<script lang="ts">
  export let title: string = "Overview";
</script>

<div class="wrapper">
  <div class="container">
    <div class="info-box">
      <div class="info-header">
        <h3>{title}</h3>
      </div>
      <div class="info-content">
        <p>
          Our oracle service ensures transparent valuation events for vaults, updated every 60 minutes. It collects data across protocols, converts it into the liquid value in the underlying token—reflecting what the protocol would return if positions were liquidated—and aggregates it into a clear, unified total. Each snapshot includes a detailed breakdown of all positions and a clear explanation of the calculation method, making the fund's valuation process fully transparent and precise.
        </p>
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
    margin-bottom: 1.5rem;
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
    width: 100%;
  }

  .info-content p {
    margin: 0;
    line-height: 1.6;
    font-size: 0.875rem;
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
      text-align: center;
    }

    .info-content {
      text-align: center;
    }

    .info-content p {
      max-width: 90%;
      margin: 0 auto;
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