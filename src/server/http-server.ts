import { EventEmitter } from 'events';
import express, { Request, Response } from 'express';
import { Config, StreamableServerConfig } from '../config/config.js';
import { Logger } from '../utils/logger.js';
import { MCPClientManager } from '../client/mcp-client-manager.js';
import { TunnelManager } from '../utils/tunnel.js';
import { StreamSessionManager } from '../stream/session-manager.js';
import type { StreamSession } from '../stream/stream-session.js';
import type { JSONRPCMessage } from '@modelcontextprotocol/sdk/types.js';

export class HttpServer {
  private app = express();
  private readonly config: Config;
  private readonly logger: Logger;
  private readonly mcpClient: MCPClientManager;
  private readonly accessToken: string;
  private readonly allowedOrigins: string[];
  private tunnelManager?: TunnelManager;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private streamSessionCleanupTimer: NodeJS.Timeout | null = null;
  private bridgeCleanupTimer: NodeJS.Timeout | null = null;
  private clientCache: Map<string, {
    id: string,
    lastUsed: number,
    env?: Record<string, string>
  }> = new Map();
  private readonly CLIENT_CACHE_TTL = 5 * 60 * 1000; // five minutes caching time
  private readonly CLEANUP_INTERVAL_DIVISOR = 3; // Run cleanup every TTL/3
  private readonly streamSessionManager: StreamSessionManager;
  private readonly streamableServers: Record<string, StreamableServerConfig>;

  constructor(config: Config, logger: Logger, mcpClient: MCPClientManager) {
    this.config = config;
    this.logger = logger;
    this.mcpClient = mcpClient;
    
    EventEmitter.defaultMaxListeners = 15;
    
    this.accessToken = this.config.security.authToken;
    this.allowedOrigins = this.config.security.allowedOrigins;
    if (!this.accessToken) {
      this.logger.warn('No AUTH_TOKEN environment variable set. This is a security risk.');
    }

    if (process.argv.includes('--tunnel')) {
      this.tunnelManager = new TunnelManager(logger);
    }

    this.streamableServers = this.config.streamable.servers;
    this.streamSessionManager = new StreamSessionManager(
      this.logger,
      this.config.streamable.sessionTtlMs
    );

    this.setupMiddleware();
    this.setupRoutes();

    this.setupHeartbeat();
    this.setupCleanupTimers();
  }

  private setupHeartbeat() {
    this.reconnectTimer = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:${this.config.server.port}/health`);
        if (!response.ok) {
          throw new Error(`Health check failed with status: ${response.status}`);
        }
      } catch (error) {
        this.logger.warn('Health check failed, restarting server...', error);
        await this.start().catch(startError => {
          this.logger.error('Failed to restart server:', startError);
        });
      }
    }, 30000); 
  }

  private setupCleanupTimers() {
    // Check if cleanup is disabled via environment variable
    const disableBridgeCleanup = process.env.DISABLE_BRIDGE_CLEANUP === 'true';
    const disableStreamCleanup = process.env.DISABLE_STREAM_CLEANUP === 'true';

    if (!disableBridgeCleanup) {
      // Run bridge cleanup every TTL/3 to catch expired sessions more frequently
      // This reduces the window where an expired session might still be used
      const bridgeCleanupInterval = Math.floor(this.CLIENT_CACHE_TTL / this.CLEANUP_INTERVAL_DIVISOR);
      this.bridgeCleanupTimer = setInterval(
        () => this.cleanupClientCache(),
        bridgeCleanupInterval
      );
      this.logger.info(`Bridge session cleanup enabled (interval: ${bridgeCleanupInterval}ms, TTL: ${this.CLIENT_CACHE_TTL}ms)`);
    } else {
      this.logger.warn('Bridge session cleanup is DISABLED - sessions will not be automatically cleaned up');
    }

    if (!disableStreamCleanup) {
      // Run streamable cleanup every TTL/3
      const streamCleanupInterval = Math.floor(this.config.streamable.sessionTtlMs / this.CLEANUP_INTERVAL_DIVISOR);
      this.streamSessionCleanupTimer = setInterval(
        () => this.streamSessionManager.reapExpiredSessions(),
        streamCleanupInterval
      );
      this.logger.info(`Streamable session cleanup enabled (interval: ${streamCleanupInterval}ms, TTL: ${this.config.streamable.sessionTtlMs}ms)`);
    } else {
      this.logger.warn('Streamable session cleanup is DISABLED - sessions will not be automatically cleaned up');
    }
  }

  private setupMiddleware(): void {
    // JSON body parser
    this.app.use(express.json());

    // Health check endpoint
    this.app.get('/health', (req: Request, res: Response) => {
      res.json({ status: 'ok' });
    });

    // Bearer Token Authentication middleware
    this.app.use((req: Request, res: Response, next) => {
      if (this.allowedOrigins.length > 0) {
        const origin = req.headers.origin;
        if (origin && !this.allowedOrigins.includes(origin)) {
          this.logger.warn(`Rejected request due to origin mismatch: ${origin}`);
          res.status(403).json({ error: 'Origin not allowed' });
          return;
        }
      }

      const authHeader = req.headers.authorization;
      // If no auth header, check if access token is set
      if (this.accessToken) {
        if (!authHeader) {
          res.status(401).json({ error: 'Authorization header is required' });
          return;
        } else {
          // If auth header is set, check if it's a valid Bearer token
          if (authHeader) {
            const [type, token] = authHeader.split(' ');
            if (type !== 'Bearer') {
              res.status(401).json({ error: 'Authorization type must be Bearer' });
              return;
            }

            if (!token || token !== this.accessToken) {
              res.status(401).json({ error: 'Invalid access token' });
              return;
            }
          } else {
            res.status(401).json({ error: 'Access token is required' });
            return;
          }
        }
      }
      next();
    });

    // Error handling middleware
    this.app.use((err: Error, req: Request, res: Response, next: any) => {
      this.logger.error('Server error:', err);
      res.status(500).json({ error: 'Internal server error' });
    });
  }

  private maskSensitiveData(data: any): any {
    if (!data) return data;
    const masked = { ...data };
    if (masked.env && typeof masked.env === 'object') {
      masked.env = Object.keys(masked.env).reduce((acc, key) => {
        acc[key] = '********';
        return acc;
      }, {} as Record<string, string>);
    }
    return masked;
  }

  private setupRoutes(): void {
    // Bridge endpoint
    this.app.post('/bridge', async (req: Request, res: Response) => {
      let clientId: string | undefined;
      try {
        const { serverPath, method, params, args, env } = req.body;
        
        this.logger.info('Bridge request received:', this.maskSensitiveData(req.body));
        if (!serverPath || !method || !params) {
          res.status(400).json({ 
            error: 'Invalid request body. Required: serverPath, method, params. Optional: args' 
          });
          return;
        }

        // Generate cache key
        const cacheKey = `${serverPath}-${JSON.stringify(args)}-${JSON.stringify(env)}`;
        const cachedClient = this.clientCache.get(cacheKey);

        if (cachedClient) {
          try {
            // Test if the connection is still valid
            await this.mcpClient.executeRequest(cachedClient.id, 'ping', {});
            clientId = cachedClient.id;
            cachedClient.lastUsed = Date.now();
          } catch (error) {
            // If the connection is invalid, delete the cache and create a new one
            await this.mcpClient.closeClient(cachedClient.id).catch(() => {});
            this.clientCache.delete(cacheKey);
            clientId = await this.mcpClient.createClient(serverPath, args, env);
            this.clientCache.set(cacheKey, {
              id: clientId,
              lastUsed: Date.now(),
              env
            });
          }
        } else {
          // Create new client
          clientId = await this.mcpClient.createClient(serverPath, args, env);
          this.clientCache.set(cacheKey, {
            id: clientId,
            lastUsed: Date.now(),
            env
          });
        }

        // Execute request
        const response = await this.mcpClient.executeRequest(clientId, method, params);
        res.json(response);

      } catch (error) {
        this.logger.error('Error processing bridge request:', error);
        res.status(500).json({ error: 'Failed to process request' });
      }
    });

    this.app.post('/mcp/:serverId', (req: Request, res: Response) => {
      this.logger.info(`MCP request received for serverId: ${req.params.serverId}`);
      void this.handleStreamablePost(req, res);
    });

    this.app.get('/mcp/:_serverId', (req: Request, res: Response) => {
      res.status(405).json({ error: 'GET not supported for MCP endpoint' });
    });

    this.app.delete('/mcp/:_serverId', async (req: Request, res: Response) => {
      const sessionIdHeader = req.header('mcp-session-id');
      if (!sessionIdHeader) {
        res.status(400).json({ error: 'mcp-session-id header required' });
        return;
      }

      await this.streamSessionManager.closeSession(sessionIdHeader).catch((error) => {
        this.logger.error('Failed to close session:', error);
      });
      res.status(204).end();
    });
  }

  public async start(): Promise<void> {
    const banner = `
    ███╗   ███╗ ██████╗██████╗      ██████╗ ██████╗ ███╗   ██╗███╗   ██╗███████╗ ██████╗████████╗
    ████╗ ████║██╔════╝██╔══██╗    ██╔════╝██╔═══██╗████╗  ██║████╗  ██║██╔════╝██╔════╝╚══██╔══╝
    ██╔████╔██║██║     ██████╔╝    ██║     ██║   ██║██╔██╗ ██║██╔██╗ ██║█████╗  ██║        ██║   
    ██║╚██╔╝██║██║     ██╔═══╝     ██║     ██║   ██║██║╚██╗██║██║╚██╗██║██╔══╝  ██║        ██║   
    ██║ ╚═╝ ██║╚██████╗██║         ╚██████╗╚██████╔╝██║ ╚████║██║ ╚████║███████╗╚██████╗   ██║   
    ╚═╝     ╚═╝ ╚═════╝╚═╝          ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═══╝╚══════╝ ╚═════╝   ╚═╝   
    `;
    
    return new Promise((resolve, reject) => {
      try {
        const server = this.app.listen(this.config.server.port, async () => {
          try {
            console.log('\x1b[36m%s\x1b[0m', banner);
            const localUrl = `http://localhost:${this.config.server.port}`;
            this.logger.info(`Server listening on port ${this.config.server.port}`);
            this.logger.info(`Local: ${localUrl}`);
            this.logger.info(`Health check URL: ${localUrl}/health`);
            this.logger.info(`MCP Bridge URL: ${localUrl}/bridge`);

            if (this.tunnelManager) {
              try {
                const url = await this.tunnelManager.createTunnel(this.config.server.port);
                if (url) {
                  this.logger.info(`Tunnel URL: ${url}`);
                  this.logger.info(`MCP Bridge URL: ${url}/bridge`);
                }
              } catch (error) {
                this.logger.error('Failed to create tunnel:', error);
                // Don't reject here as tunnel is optional
              }
            }
            resolve();
          } catch (error) {
            this.logger.error('Error during server startup:', error);
            server.close();
            reject(error);
          }
        });

        server.on('error', (error: Error) => {
          this.logger.error('Server failed to start:', error);
          reject(error);
        });
      } catch (error) {
        this.logger.error('Critical error during server initialization:', error);
        reject(error);
      }
    });
  }

  public async stop(): Promise<void> {
    if (this.reconnectTimer) {
      clearInterval(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.bridgeCleanupTimer) {
      clearInterval(this.bridgeCleanupTimer);
      this.bridgeCleanupTimer = null;
    }

    // Close all cached clients
    const closePromises = Array.from(this.clientCache.values()).map(async (client) => {
      try {
        await this.mcpClient.closeClient(client.id);
      } catch (error) {
        this.logger.error(`Error closing client ${client.id}:`, error);
      }
    });

    await Promise.all(closePromises);
    this.clientCache.clear();

    if (this.streamSessionCleanupTimer) {
      clearInterval(this.streamSessionCleanupTimer);
      this.streamSessionCleanupTimer = null;
    }

    await this.streamSessionManager.closeAll();

    if (this.tunnelManager) {
      await this.tunnelManager.disconnect();
    }
  }

  private getStreamableServer(serverId: string): StreamableServerConfig | undefined {
    return this.streamableServers[serverId];
  }

  private acceptHeaderSupportsStreaming(headerValue: string | undefined): boolean {
    if (!headerValue) {
      return false;
    }

    const values = headerValue
      .split(',')
      .map((value) => value.split(';')[0].trim().toLowerCase())
      .filter((value) => value.length > 0);

    return values.includes('application/json') && values.includes('text/event-stream');
  }

  private isJsonRpcRequest(message: JSONRPCMessage): message is Extract<JSONRPCMessage, { method: string; id: unknown }> {
    return (
      typeof (message as { method?: unknown }).method === 'string' &&
      Object.prototype.hasOwnProperty.call(message, 'id')
    );
  }

  private isJsonRpcResponse(message: JSONRPCMessage): message is Extract<JSONRPCMessage, { id: unknown }> {
    const hasId = Object.prototype.hasOwnProperty.call(message, 'id');
    const hasResult = Object.prototype.hasOwnProperty.call(message, 'result');
    const hasError = Object.prototype.hasOwnProperty.call(message, 'error');
    return hasId && (hasResult || hasError) && !Object.prototype.hasOwnProperty.call(message, 'method');
  }

  private async handleStreamablePost(req: Request, res: Response): Promise<void> {
    this.logger.info(`Streamable request received: ${req.method} ${req.originalUrl}`);
    const serverId = req.params.serverId;
    const serverConfig = this.getStreamableServer(serverId);
    if (!serverConfig) {
      this.logger.warn(`Streamable request received for unknown serverId: ${serverId}`);
      res.status(404).json({ error: `Unknown MCP server: ${serverId}` });
      return;
    }
    if (!this.acceptHeaderSupportsStreaming(req.headers.accept)) {
      res.status(406).json({ error: 'Accept header must include application/json and text/event-stream' });
      return;
    }

    const payload = req.body;
    const messages = Array.isArray(payload) ? payload : [payload];
    if (!messages || messages.length === 0) {
      res.status(400).json({ error: 'Request body must include at least one JSON-RPC message' });
      return;
    }

    if (messages.some((message) => typeof message !== 'object' || message === null)) {
      res.status(400).json({ error: 'Each JSON-RPC message must be an object' });
      return;
    }
    const normalizedMessages = messages as JSONRPCMessage[];
    const hasRequests = normalizedMessages.some((message) => this.isJsonRpcRequest(message));
    const sessionHeader = req.header('mcp-session-id');

    let session: StreamSession | undefined;
    let sessionId: string;

    try {
      this.logger.info(`Session header: ${sessionHeader}, hasRequests: ${hasRequests}`);
      if (!sessionHeader) {
        if (!hasRequests) {
          res.status(400).json({ error: 'mcp-session-id header required when request body has no requests' });
          return;
        }

        session = await this.streamSessionManager.createSession(serverId, serverConfig);
        sessionId = session.id;
      } else {
        session = this.streamSessionManager.getSession(sessionHeader, serverId);
        if (!session) {
          res.status(404).json({ error: 'Session not found' });
          return;
        }
        await session.ensureStarted();
        sessionId = sessionHeader;
      }
    } catch (error) {
      res.status(500).json({ error: 'Failed to establish session with MCP server' });
      return;
    }
    res.setHeader('mcp-session-id', sessionId);

    const forwardMessages = async () => {
      for (const message of normalizedMessages) {
        await session!.send(message);
      }
    };

    if (!hasRequests) {
      try {
        await forwardMessages();
        res.status(202).end();
      } catch (error) {
        res.status(500).json({ error: 'Failed to forward messages to MCP server' });
      }
      return;
    }

    res.status(200);
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    if (typeof (res as any).flushHeaders === 'function') {
      (res as any).flushHeaders();
    } else {
      res.write('\n');
    }

    const pendingIds = new Set<string>();
    for (const message of normalizedMessages) {
      if (this.isJsonRpcRequest(message)) {
        pendingIds.add(String(message.id));
      }
    }

    let streamClosed = false;
    let eventCounter = 0;

    const writeEvent = (payload: unknown, eventType = 'message') => {
      if (streamClosed || res.writableEnded) {
        return;
      }
      try {
        res.write(`event: ${eventType}\n`);
        res.write(`id: ${++eventCounter}\n`);
        res.write(`data: ${JSON.stringify(payload)}\n\n`);
      } catch (error) {
        this.logger.error('Error writing SSE frame:', error);
      }
    };

    const cleanup = () => {
      if (streamClosed) {
        return;
      }
      streamClosed = true;
      session?.off('message', onSessionMessage);
      session?.off('error', onSessionError);
      session?.off('close', onSessionClose);
      req.off('close', onClientClose);
      if (!res.writableEnded) {
        res.end();
      }
    };

    const deliverMessage = (message: JSONRPCMessage) => {
      let shouldCloseAfterWrite = false;
      if (this.isJsonRpcResponse(message)) {
        const key = String(message.id);
        if (!pendingIds.has(key)) {
          return;
        }
        pendingIds.delete(key);
        shouldCloseAfterWrite = pendingIds.size === 0;
      }

      writeEvent(message);

      if (shouldCloseAfterWrite) {
        cleanup();
      }
    };

    const onSessionMessage = (payload: JSONRPCMessage | JSONRPCMessage[]) => {
      if (Array.isArray(payload)) {
        payload.forEach((message) => deliverMessage(message));
      } else {
        deliverMessage(payload);
      }
    };

    const onSessionError = (error: Error) => {
      writeEvent({ error: error.message }, 'error');
      cleanup();
    };

    const onSessionClose = () => {
      cleanup();
    };

    const onClientClose = () => {
      cleanup();
    };

    session.on('message', onSessionMessage);
    session.on('error', onSessionError);
    session.on('close', onSessionClose);
    req.on('close', onClientClose);

    try {
      await forwardMessages();
    } catch (error) {
      this.logger.error('Failed to forward JSON-RPC request batch:', error);
      writeEvent({ error: 'Failed to forward request to MCP server' }, 'error');
      cleanup();
    }
  }

  private async cleanupClientCache(): Promise<void> {
    const now = Date.now();
    const expiredClients: Array<{ key: string; clientId: string; idleTime: number }> = [];

    // First pass: identify expired clients
    for (const [key, value] of this.clientCache.entries()) {
      const idleTime = now - value.lastUsed;
      if (idleTime > this.CLIENT_CACHE_TTL) {
        expiredClients.push({ key, clientId: value.id, idleTime });
      }
    }

    if (expiredClients.length === 0) {
      return;
    }

    this.logger.info(`Cleaning up ${expiredClients.length} expired bridge client(s)`);

    // Second pass: close expired clients
    for (const { key, clientId, idleTime } of expiredClients) {
      try {
        this.logger.debug(`Closing bridge client ${clientId} (idle for ${Math.floor(idleTime / 1000)}s)`);
        await this.mcpClient.closeClient(clientId).catch(err => {
          this.logger.error(`Error closing client ${clientId}:`, err);
        });
        this.clientCache.delete(key);
      } catch (error) {
        this.logger.error(`Error during cleanup for client ${clientId}:`, error);
        this.clientCache.delete(key);
      }
    }
  }
}
