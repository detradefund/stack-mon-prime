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
          Our oracle service ensures transparent valuation events for vaults, updated every 30 minutes. It collects data across protocols, converts it into the liquid value in the underlying token—reflecting what the protocol would return if positions were liquidated—and aggregates it into a clear, unified total. Each snapshot includes a detailed breakdown of all positions and a clear explanation of the calculation method, making the fund's valuation process fully transparent and precise.
        </p>
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
      text-align: center;
    }

    .info-header {
      display: flex;
      justify-content: center;
    }

    .info-content {
      display: flex;
      flex-direction: column;
      align-items: center;
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