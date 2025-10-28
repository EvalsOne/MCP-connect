import * as dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import { HttpServer } from './server/http-server.js';
import { MCPClientManager } from './client/mcp-client-manager.js';
import { Config, loadConfig } from './config/config.js';
import { Logger, createLogger } from './utils/logger.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const result = dotenv.config({ 
  path: path.resolve(__dirname, '../.env'),
  override: true  // 强制覆盖已存在的环境变量
});

if (result.error) {
  console.error('Error loading .env file:', result.error);
  process.exit(1);
}

async function main() {
  const config =  loadConfig();
  const logger = createLogger(config);
  const mcpClient = new MCPClientManager(logger);
  const server = new HttpServer(config, logger, mcpClient);

  // Handle process termination
  async function shutdown() {
    logger.info('Shutting down...');
    try {
      await mcpClient.stop();
    } catch (error) {
      logger.error('Error during shutdown:', error);
    } finally {
      process.exit(0);
    }
  }

  // Handle different termination signals
  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
  process.on('uncaughtException', async (error) => {
    logger.error('Uncaught exception:', error);
    await shutdown();
  });
  process.on('unhandledRejection', async (error) => {
    logger.error('Unhandled rejection:', error);
    await shutdown();
  });

  // Start the server
  server.start();
}

main().catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});