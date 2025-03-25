export type Network = {
    id: number;
    name: string;
    icon: string;
    rpcUrl: string;
    currency: string;
    explorerUrl: string;
  };
  
  export const NETWORKS: { [key: number]: Network } = {
    1: {
      id: 1,
      name: 'Ethereum',
      icon: '/ethereum.svg',
      rpcUrl: 'https://mainnet.infura.io/v3/your-project-id',
      currency: 'ETH',
      explorerUrl: 'https://etherscan.io'
    },
    8453: {
      id: 8453,
      name: 'Base',
      icon: '/base.png',
      rpcUrl: 'https://mainnet.base.org',
      currency: 'ETH',
      explorerUrl: 'https://basescan.org'
    }
  };
  
  export const SUPPORTED_CHAIN_IDS = Object.keys(NETWORKS).map(Number); 