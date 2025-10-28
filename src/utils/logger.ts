import winston from 'winston';
import { Config } from '../config/config.js';

export function createLogger(config: Config) {
  return winston.createLogger({
    level: config.logging.level,
    format: winston.format.combine(
      // winston.format.timestamp(),
      winston.format.json()
    ),
    transports: [
      new winston.transports.Console({
        format: winston.format.combine(
          winston.format.colorize(),
          winston.format.simple()
        ),
      }),
      new winston.transports.File({ 
        filename: 'error.log', 
        level: 'error' 
      }),
      new winston.transports.File({ 
        filename: 'combined.log' 
      })
    ],
  });
}

export type Logger = ReturnType<typeof createLogger>; 