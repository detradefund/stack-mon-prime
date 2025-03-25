import { writable } from 'svelte/store';
import { ethers } from 'ethers';
import type { Contract } from 'ethers';
import { signer } from './wallet';
import vaultABI from '$lib/abis/VaultABI.json';

// Create a writable store for the vault contract
export const vaultContract = writable<Contract | null>(null);

// Initialize the contract when signer changes
signer.subscribe(($signer) => {
  if ($signer && window.location.pathname.includes('/vault/')) {
    const vaultAddress = window.location.pathname.split('/').pop();
    if (vaultAddress) {
      const contract = new ethers.Contract(vaultAddress, vaultABI, $signer);
      vaultContract.set(contract);
    }
  } else {
    vaultContract.set(null);
  }
}); 