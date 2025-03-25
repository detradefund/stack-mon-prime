/// <reference types="@sveltejs/kit" />

interface Window {
    ethereum?: {
        request: (args: { method: string; params?: any[] }) => Promise<any>;
        on: (event: string, callback: (params: any) => void) => void;
        removeListener: (event: string, callback: (params: any) => void) => void;
    };
}

// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
