import { spawn } from 'child_process';

/**
 * Wrapper for n8n-mcp to ensure that only JSON lines are written to stdout.
 * Any non-JSON output (e.g. banners, help text) is redirected to stderr
 * so that the MCP stdio transport sees a clean JSON-RPC stream.
 */
const child = spawn('npx', ['n8n-mcp'], {
  stdio: ['pipe', 'pipe', 'inherit'],
  env: process.env,
});

process.stdin.pipe(child.stdin);

let buffer = '';
if (child.stdout) {
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', (chunk: string) => {
    buffer += chunk;

    let newlineIndex: number;
    while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, newlineIndex);
      buffer = buffer.slice(newlineIndex + 1);

      const trimmed = line.trim();
      if (!trimmed) {
        continue;
      }

      // Heuristic: JSON-RPC messages should start with { or [
      if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
        process.stdout.write(trimmed + '\n');
      } else {
        // Avoid flooding logs; just emit a short notice to stderr
        console.error(
          '[n8n-mcp-wrapper] filtered non-JSON stdout:',
          trimmed.length > 120 ? `${trimmed.slice(0, 117)}...` : trimmed,
        );
      }
    }
  });
}

child.on('exit', (code, signal) => {
  if (code !== null) {
    process.exit(code);
  } else if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(0);
  }
});

child.on('error', (error) => {
  console.error('[n8n-mcp-wrapper] failed to start n8n-mcp:', error);
  process.exit(1);
});

