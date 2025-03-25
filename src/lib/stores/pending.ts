import { writable } from 'svelte/store';

interface PendingState {
  isTransactionPending: boolean;
  transactionHash?: string;
}

export const pendingTransaction = writable<PendingState>({
  isTransactionPending: false
}); 