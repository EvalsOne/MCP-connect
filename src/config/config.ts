import dotenv from 'dotenv';
import path from 'path';

// Load environment variables
dotenv.config();

export interface Config {
  server: {
    port: number;
  };
  security: {
    authToken: string;
  };
  logging: {
    level: string;
  };
}

function validateConfig(config: Config): void {
  if (!config.server.port) {
    throw new Error('PORT is required');
  }
}

export function loadConfig(): Config {
  const config: Config = {
    server: {
      port: parseInt(process.env.PORT || '3000', 10),
    },
    security: {
      authToken: process.env.AUTH_TOKEN || '',
    },
    logging: {
      level: process.env.LOG_LEVEL || 'INFO',
    },
  };

  validateConfig(config);
  return config;
} 