import { StreamSession } from './stream-session.js';
import type { StreamableServerConfig } from '../config/config.js';
import type { Logger } from '../utils/logger.js';

interface SessionRecord {
  serverId: string;
  session: StreamSession;
}

export class StreamSessionManager {
  private readonly sessions = new Map<string, SessionRecord>();
  private readonly logger: Logger;
  private readonly ttlMs: number;

  constructor(logger: Logger, ttlMs: number) {
    this.logger = logger;
    this.ttlMs = ttlMs;
  }

  public async createSession(serverId: string, config: StreamableServerConfig): Promise<StreamSession> {
    const session = new StreamSession(this.logger, config);
    const sessionId = session.id;
    this.sessions.set(sessionId, { serverId, session });
    session.on('close', () => {
      this.sessions.delete(sessionId);
    });
    session.on('error', () => {
      // Errors are already logged by the session. Ensure the entry eventually clears.
      if (!this.sessions.has(sessionId)) {
        return;
      }
      // No immediate deletion; allow client to handle recovery.
    });
    await session.ensureStarted();
    this.logger.info(`Created stream session ${sessionId} for server ${serverId}`);
    return session;
  }

  public getSession(sessionId: string, serverId?: string): StreamSession | undefined {
    const record = this.sessions.get(sessionId);
    if (!record) {
      return undefined;
    }

    if (serverId && record.serverId !== serverId) {
      return undefined;
    }

    return record.session;
  }

  public async closeSession(sessionId: string): Promise<void> {
    const record = this.sessions.get(sessionId);
    if (!record) {
      return;
    }

    this.sessions.delete(sessionId);
    await record.session.close();
  }

  public reapExpiredSessions(): void {
    const now = Date.now();
    for (const [sessionId, record] of this.sessions.entries()) {
      if (now - record.session.lastUsed > this.ttlMs) {
        this.logger.info(`Closing idle session ${sessionId}`);
        void this.closeSession(sessionId).catch((error) => {
          this.logger.error(`Failed to close session ${sessionId}:`, error);
        });
      }
    }
  }

  public async closeAll(): Promise<void> {
    const ids = Array.from(this.sessions.keys());
    await Promise.all(ids.map((id) => this.closeSession(id)));
  }
}
