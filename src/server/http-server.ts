import { EventEmitter } from 'events';
import express, { Request, Response } from 'express';
import { Config } from '../config/config.js';
import { Logger } from '../utils/logger.js';
import { MCPClientManager } from '../client/mcp-client-manager.js';
import { TunnelManager } from '../utils/tunnel.js';

export class HttpServer {
  private app = express();
  private readonly config: Config;
  private readonly logger: Logger;
  private readonly mcpClient: MCPClientManager;
  private readonly accessToken: string;
  private tunnelManager?: TunnelManager;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private clientCache: Map<string, {
    id: string,
    lastUsed: number,
    env?: Record<string, string>
  }> = new Map();
  private readonly CLIENT_CACHE_TTL = 5 * 60 * 1000; // five minutes caching time

  constructor(config: Config, logger: Logger, mcpClient: MCPClientManager) {
    this.config = config;
    this.logger = logger;
    this.mcpClient = mcpClient;
    
    EventEmitter.defaultMaxListeners = 15;
    
    this.accessToken = process.env.ACCESS_TOKEN || '';
    if (!this.accessToken) {
      this.logger.warn('No ACCESS_TOKEN environment variable set. This is a security risk.');
    }
    
    if (process.argv.includes('--tunnel')) {
      this.tunnelManager = new TunnelManager(logger);
    }
    
    this.setupMiddleware();
    this.setupRoutes();

    this.setupHeartbeat();

    setInterval(() => this.cleanupClientCache(), this.CLIENT_CACHE_TTL);
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

  private setupMiddleware(): void {
    // JSON body parser
    this.app.use(express.json());

    // Health check endpoint
    this.app.get('/health', (req: Request, res: Response) => {
      res.json({ status: 'ok' });
    });

    // Bearer Token Authentication middleware
    this.app.use((req: Request, res: Response, next) => {
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
            this.logger.debug(`Using cached client: ${clientId}`);
          } catch (error) {
            // If the connection is invalid, delete the cache and create a new one
            this.logger.warn(`Cached client ${cachedClient.id} is invalid, creating new one`);
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
          this.logger.info(`Created new client: ${clientId}`);
        }

        // Execute request
        const response = await this.mcpClient.executeRequest(clientId, method, params);
        res.json(response);

      } catch (error) {
        this.logger.error('Error processing bridge request:', error);
        res.status(500).json({ error: 'Failed to process request' });
      }
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
    
    if (this.tunnelManager) {
      await this.tunnelManager.disconnect();
    }
  }

  private async cleanupClientCache(): Promise<void> {
    const now = Date.now();
    for (const [key, value] of this.clientCache.entries()) {
      try {
        if (now - value.lastUsed > this.CLIENT_CACHE_TTL) {
          await this.mcpClient.closeClient(value.id).catch(err => {
            this.logger.error(`Error closing client ${value.id}:`, err);
          });
          this.clientCache.delete(key);
          this.logger.debug(`Cleaned up cached client: ${key}`);
        }
      } catch (error) {
        this.logger.error(`Error during cleanup for client ${value.id}:`, error);
        this.clientCache.delete(key);
      }
    }
  }
}