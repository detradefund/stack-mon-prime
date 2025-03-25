import { json } from '@sveltejs/kit';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function POST() {
    try {
        // Exécuter le script Python
        const { stdout, stderr } = await execAsync('python detrade-core-usdc/builder/balance_pusher.py');
        
        if (stderr) {
            console.error('Script error:', stderr);
            return json({ error: stderr }, { status: 500 });
        }

        return json({ success: true, output: stdout });
    } catch (error) {
        console.error('Execution error:', error);
        return json({ error: error.message }, { status: 500 });
    }
} 