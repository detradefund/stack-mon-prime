import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 3000,
		host: true
	},
	envPrefix: [
		'VITE_',
		'MONGO_URI',
		'DATABASE_NAME_1',
		'COLLECTION_NAME'
	]
});
