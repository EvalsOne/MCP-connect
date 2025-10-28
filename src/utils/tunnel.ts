import ngrok from 'ngrok';
import { Logger } from './logger.js';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export class TunnelManager {
  private logger: Logger;
  private url: string | null = null;
  private retryCount = 0;
  private readonly maxRetries = 3;

  constructor(logger: Logger) {
    this.logger = logger;
  }

  async createTunnel(port: number): Promise<string | null> {
    if (!process.env.NGROK_AUTH_TOKEN) {
      this.logger.error('NGROK_AUTH_TOKEN is not set in environment variables');
      return null;
    }

    try {
      // Clean up existing ngrok processes
      this.logger.info('Cleaning up existing ngrok processes...');
      await ngrok.kill();
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Reset authtoken
      this.logger.info('Setting up ngrok authentication...');
      await ngrok.authtoken(process.env.NGROK_AUTH_TOKEN);

      // Use the simplest configuration to connect
      this.logger.info(`========================================`);
      this.logger.info(`Starting ngrok tunnel for port ${port}...`);
      this.url = await ngrok.connect({
        addr: port,
        authtoken: process.env.NGROK_AUTH_TOKEN
      });

      if (this.url) {
        this.logger.info('Ngrok tunnel established successfully');
        return this.url;
      }

      throw new Error('Failed to get tunnel URL');

    } catch (error) {
      this.logger.error('Tunnel creation failed:', error);

      if (this.retryCount < this.maxRetries) {
        this.retryCount++;
        this.logger.info(`Retrying... (${this.retryCount}/${this.maxRetries})`);
        await new Promise(resolve => setTimeout(resolve, 2000));
        return this.createTunnel(port);
      }

      // If all attempts fail, use the command line method
      try {
        this.logger.info('Attempting to start ngrok using CLI...');
        const { stdout } = await execAsync(`npx ngrok http ${port} --log=stdout`);
        this.logger.debug('Ngrok CLI output:', stdout);
        
        const match = stdout.match(/https:\/\/[a-zA-Z0-9-]+\.ngrok\.io/);
        if (match) {
          this.url = match[0];
          this.logger.info(`Tunnel established via CLI: ${this.url}`);
          return this.url;
        }
      } catch (cliError) {
        this.logger.error('CLI fallback also failed:', cliError);
      }

      return null;
    }
  }

  async disconnect(): Promise<void> {
    if (this.url) {
      try {
        await ngrok.disconnect(this.url);
        await ngrok.kill();
        this.logger.info('Ngrok tunnel disconnected');
        this.url = null;
      } catch (error: any) {
        this.logger.error('Error disconnecting ngrok tunnel:', error);
        this.url = null;
        await ngrok.kill().catch(() => {});
        throw error;
      }
    }
  }
}