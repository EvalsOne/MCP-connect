import dotenv from 'dotenv';
import path from 'path';
import fs from 'fs';
import yaml from 'js-yaml';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
dotenv.config();

export interface StreamableServerConfig {
  command: string;
  args?: string[];
  env?: Record<string, string>;
  description?: string;
  timeout?: number;
  retries?: number;
}

export interface Config {
  server: {
    port: number;
  };
  security: {
    authToken: string;
    allowedOrigins: string[];
  };
  logging: {
    level: string;
  };
  streamable: {
    sessionTtlMs: number;
    servers: Record<string, StreamableServerConfig>;
  };
}

function validateConfig(config: Config): void {
  if (!config.server.port) {
    throw new Error('PORT is required');
  }

  if (Number.isNaN(config.streamable.sessionTtlMs) || config.streamable.sessionTtlMs <= 0) {
    throw new Error('STREAM_SESSION_TTL_MS must be a positive integer');
  }
}

/**
 * Resolve environment variable references in a string
 * Example: "postgresql://${DB_USER}:${DB_PASS}@localhost"
 */
function resolveEnvVars(value: string): string {
  return value.replace(/\$\{([^}]+)\}/g, (_, envVar) => {
    return process.env[envVar] || '';
  });
}

/**
 * Recursively resolve environment variables in an object
 */
function resolveEnvVarsInObject(obj: any): any {
  if (typeof obj === 'string') {
    return resolveEnvVars(obj);
  }
  if (Array.isArray(obj)) {
    return obj.map(resolveEnvVarsInObject);
  }
  if (obj && typeof obj === 'object') {
    const result: any = {};
    for (const [key, value] of Object.entries(obj)) {
      result[key] = resolveEnvVarsInObject(value);
    }
    return result;
  }
  return obj;
}

function parseServers(): Record<string, StreamableServerConfig> {
  // Priority 1: Load from JSON file
  const configPaths = [
    path.resolve(process.cwd(), 'mcp-servers.json'),
  ];

  for (const configPath of configPaths) {
    if (fs.existsSync(configPath)) {
      try {
        const content = fs.readFileSync(configPath, 'utf8');
        let parsed: any;

        parsed = JSON.parse(content);

        // Support both "mcpServers" (MCP standard) and "servers" (legacy) keys
        const servers = parsed.mcpServers || parsed.servers || parsed;

        // Validate and resolve env vars
        const resolvedServers: Record<string, StreamableServerConfig> = {};
        for (const [key, value] of Object.entries(servers)) {
          if (!value || typeof value !== 'object') {
            throw new Error(`Invalid server definition for key "${key}"`);
          }
          const config = value as any;
          if (!config.command) {
            throw new Error(`Missing command for server "${key}"`);
          }

          // Resolve environment variable references
          resolvedServers[key] = resolveEnvVarsInObject(config);
        }

        console.log(`✓ Loaded MCP servers from ${configPath}`);
        return resolvedServers;
      } catch (error) {
        throw new Error(`Failed to parse ${configPath}: ${String(error)}`);
      }
    }
  }

  // Priority 2: Fallback to MCP_SERVERS environment variable (legacy)
  const raw = process.env.MCP_SERVERS;
  if (!raw) {
    console.log('⚠ No MCP server configuration found. Create mcp-servers.json or set MCP_SERVERS env var.');
    return {};
  }

  try {
    const parsed = JSON.parse(raw) as Record<string, StreamableServerConfig>;
    Object.entries(parsed).forEach(([key, value]) => {
      if (!value || typeof value !== 'object') {
        throw new Error(`Invalid server definition for key "${key}"`);
      }
      if (!value.command) {
        throw new Error(`Missing command for server "${key}"`);
      }
    });
    console.log('✓ Loaded MCP servers from MCP_SERVERS environment variable');
    return resolveEnvVarsInObject(parsed);
  } catch (error) {
    throw new Error(`Failed to parse MCP_SERVERS: ${String(error)}`);
  }
}

function parseAllowedOrigins(): string[] {
  const raw = process.env.ALLOWED_ORIGINS;
  if (!raw) {
    return [];
  }

  return raw
    .split(',')
    .map((origin) => origin.trim())
    .filter((origin) => origin.length > 0);
}

export function loadConfig(): Config {
  const config: Config = {
    server: {
      port: parseInt(process.env.PORT || '3000', 10),
    },
    security: {
      authToken: process.env.AUTH_TOKEN || process.env.ACCESS_TOKEN || '',
      allowedOrigins: parseAllowedOrigins(),
    },
    logging: {
      level: (process.env.LOG_LEVEL || 'info').toLowerCase(),
    },
    streamable: {
      sessionTtlMs: parseInt(process.env.STREAM_SESSION_TTL_MS || `${5 * 60 * 1000}`, 10),
      servers: parseServers(),
    },
  };

  validateConfig(config);
  return config;
} 
