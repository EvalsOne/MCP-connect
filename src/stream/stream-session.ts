import { EventEmitter } from 'events';
import { randomUUID } from 'crypto';
import { getDefaultEnvironment, StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import type { JSONRPCMessage } from '@modelcontextprotocol/sdk/types.js';
import type { StreamableServerConfig } from '../config/config.js';
import type { Logger } from '../utils/logger.js';

export class StreamSession extends EventEmitter {
  public readonly id: string;
  private readonly transport: StdioClientTransport;
  private readonly logger: Logger;
  private readonly serverConfig: StreamableServerConfig;
  private started = false;
  private closed = false;
  private stderrAttached = false;
  private _lastUsed = Date.now();

  constructor(logger: Logger, serverConfig: StreamableServerConfig, sessionId?: string) {
    super();
    this.logger = logger;
    this.serverConfig = serverConfig;
    this.id = sessionId ?? randomUUID();

    const mergedEnv = {
      ...getDefaultEnvironment(),
      ...(serverConfig.env ?? {}),
    };

    const n8nUrl = mergedEnv['N8N_API_URL'];
    const n8nKey = mergedEnv['N8N_API_KEY'];
    if (n8nUrl || n8nKey) {
      const maskedKey =
        typeof n8nKey === 'string' && n8nKey.length > 4
          ? `***${n8nKey.slice(-4)}`
          : n8nKey
            ? '***'
            : '<undefined>';
      this.logger.info(
        `Stream session ${this.id} env snapshot: N8N_API_URL=${n8nUrl ?? '<undefined>'}, N8N_API_KEY=${maskedKey}`,
      );
    }

    this.transport = new StdioClientTransport({
      command: serverConfig.command,
      args: serverConfig.args ?? [],
      env: mergedEnv,
      stderr: 'pipe',
    });

    this.transport.onmessage = (message) => {
      this._lastUsed = Date.now();
      this.emit('message', message as JSONRPCMessage);
    };

    this.transport.onclose = () => {
      this.closed = true;
      this.emit('close');
    };

    this.transport.onerror = (error) => {
      const err = error instanceof Error ? error : new Error(String(error));
      this.logger.error(`Session ${this.id} transport error:`, err);
      this.emit('error', err);
    };
  }

  public get lastUsed(): number {
    return this._lastUsed;
  }

  public async ensureStarted(): Promise<void> {
    if (this.started || this.closed) {
      return;
    }

    await this.transport.start();
    this.started = true;
    this._lastUsed = Date.now();

    if (!this.stderrAttached) {
      const stderr = this.transport.stderr;
      if (stderr) {
        const readable = stderr as unknown as NodeJS.ReadableStream;
        if (typeof readable.setEncoding === 'function') {
          readable.setEncoding('utf8');
        }
        readable.on('data', (chunk: string) => {
          const output = chunk.trim();
          if (output.length > 0) {
            this.logger.debug(`Session ${this.id} stderr: ${output}`);
          }
        });
      }
      this.stderrAttached = true;
    }
  }

  public async send(message: JSONRPCMessage): Promise<void> {
    if (this.closed) {
      throw new Error(`Session ${this.id} is closed`);
    }

    await this.ensureStarted();
    await this.transport.send(message);
    this._lastUsed = Date.now();
  }

  public async close(): Promise<void> {
    if (this.closed) {
      return;
    }

    this.closed = true;
    await this.transport.close();
    this.emit('close');
  }
}
