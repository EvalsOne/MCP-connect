import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { getDefaultEnvironment, StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { WebSocketClientTransport } from '@modelcontextprotocol/sdk/client/websocket.js';
import { Transport } from '@modelcontextprotocol/sdk/shared/transport.js';
import { 
  CallToolResultSchema,
  ClientCapabilities,
  CompleteResultSchema,
  EmptyResultSchema,
  GetPromptResultSchema,
  Implementation,
  ListPromptsResultSchema,
  ListResourcesResultSchema,
  ListResourceTemplatesResultSchema,
  ListToolsResultSchema,
  ReadResourceResultSchema,
  LATEST_PROTOCOL_VERSION,
  CompatibilityCallToolResultSchema
} from '@modelcontextprotocol/sdk/types.js';
import { Logger } from '../utils/logger.js';

export class MCPClientManager {
  private clients: Map<string, Client> = new Map();
  private transports: Map<string, Transport> = new Map();
  private readonly logger: Logger;
  private readonly clientInfo: Implementation = {
    name: "mcp-bridge",
    version: "1.0.0"
  };
  private readonly capabilities: ClientCapabilities = {
    prompts: true,
    tools: true,
    resources: {
      subscribe: true
    },
    logging: true
  };

  constructor(logger: Logger) {
    this.logger = logger;
  }

  public async createClient(serverPath: string, args?: string[], env?: Record<string, string>): Promise<string> {
    const clientId = `client_${Date.now()}`;
    this.logger.info(`Creating client ${clientId} for ${serverPath}`);
    try {
      let transport;
      
      // Check if serverPath is a URL
      let url: URL | undefined = undefined;
      try {
        url = new URL(serverPath);
      } catch {
        // Not a URL, treat as command path
      }

      if (url?.protocol === "http:" || url?.protocol === "https:") {
        transport = new SSEClientTransport(url);
      } else if (url?.protocol === "ws:" || url?.protocol === "wss:") {
        transport = new WebSocketClientTransport(url);
      } else {
        transport = new StdioClientTransport({
          command: serverPath,
          args: args || [],
          env: {
            ...getDefaultEnvironment(),
            ...(env || {})
          }
        });
      }

      const client = new Client(this.clientInfo, {
        capabilities: this.capabilities
      });

      await client.connect(transport);
      
      this.clients.set(clientId, client);
      this.transports.set(clientId, transport);
      
      return clientId;
    } catch (error) {
      this.logger.error(`Failed to create client for ${serverPath}:`, error);
      throw error;
    }
  }

  public async executeRequest(clientId: string, method: string, params: any): Promise<any> {
    const client = this.clients.get(clientId);
    if (!client) {
      throw new Error(`Client ${clientId} not found`);
    }

    try {
      this.logger.info(`Executing method: ${method}`);
      switch (method) {
        case 'completion/complete':
          return await client.complete(params);

        case 'prompts/get':
          return await client.getPrompt(params);

        case 'prompts/list':
          return await client.listPrompts(params);

        case 'resources/list':
          return await client.listResources(params);

        case 'resources/templates/list':
          return await client.listResourceTemplates(params);

        case 'resources/read':
          return await client.readResource(params);

        case 'resources/subscribe':
          return await client.subscribeResource(params);

        case 'resources/unsubscribe':
          return await client.unsubscribeResource(params);

        case 'tools/call':
          this.logger.info(`Calling tool: ${JSON.stringify(params)}`);
          return await client.callTool(
            {
              name: params.name,
              arguments: params.arguments
            },
            params.resultSchema === 'compatibility' ? CompatibilityCallToolResultSchema : CallToolResultSchema
          );

        case 'tools/list':
          return await client.listTools(params);

        case 'logging/setLevel':
          return await client.setLoggingLevel(params.level);

        case 'ping':
          return await client.ping();

        default:
          throw new Error(`Unsupported method: ${JSON.stringify(method)}`);
      }
    } catch (error) {
      this.logger.error(`Request execution error:`, error);
      throw error;
    }
  }

  public async closeClient(clientId: string): Promise<void> {
    const transport = this.transports.get(clientId);
    const client = this.clients.get(clientId);
    if (client && transport) {
      try {
        await client.close();
        await transport.close();
      } finally {
        this.transports.delete(clientId);
        this.clients.delete(clientId);
      }
    }
  }

  public async stop(): Promise<void> {
    try {
      await this.cleanup();
    } catch (error) {
      this.logger.error('Error during MCPClientManager stop:', error);
      throw error;
    }
  }

  private async cleanup(): Promise<void> {
    for (const [clientId, _] of this.clients) {
      try {
        await this.closeClient(clientId);
      } catch (error) {
        this.logger.error(`Error closing client ${clientId}:`, error);
      }
    }
    this.clients.clear();
    this.transports.clear();
  }
} 