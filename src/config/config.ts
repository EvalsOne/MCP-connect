import dotenv from 'dotenv';
import path from 'path';

// Load environment variables
dotenv.config();

export interface StreamableServerConfig {
  command: string;
  args?: string[];
  env?: Record<string, string>;
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

function parseServers(): Record<string, StreamableServerConfig> {
  const raw = process.env.MCP_SERVERS;
  if (!raw) {
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
    return parsed;
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
      level: process.env.LOG_LEVEL || 'INFO',
    },
    streamable: {
      sessionTtlMs: parseInt(process.env.STREAM_SESSION_TTL_MS || `${5 * 60 * 1000}`, 10),
      servers: parseServers(),
    },
  };

  validateConfig(config);
  return config;
} 
