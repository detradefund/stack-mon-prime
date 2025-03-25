import { dev } from '$app/environment';

export enum LogLevel {
  ERROR = 'ERROR',
  WARN = 'WARN',
  INFO = 'INFO',
  DEBUG = 'DEBUG'
}

export enum LogContext {
  WALLET = 'WALLET',
  CONTRACT = 'CONTRACT',
  UI = 'UI',
  STORE = 'STORE',
  BLOCKCHAIN = 'BLOCKCHAIN'
}

interface LogOptions {
  context: LogContext;
  data?: unknown;
}

class Logger {
  private activeGroups: Map<LogContext, boolean> = new Map();

  private formatMessage(level: LogLevel, message: string, options: LogOptions): string {
    const timestamp = new Date().toISOString();
    const context = options.context;
    return `[${timestamp}][${level}][${context}] ${message}`;
  }

  private ensureGroupStarted(context: LogContext) {
    if (!this.activeGroups.get(context)) {
      if (!Object.values(LogContext).includes(context)) {
        console.warn(`Invalid log context: ${context}`);
        return;
      }
      console.groupCollapsed(`🔍 ${context} Logs`);
      this.activeGroups.set(context, true);
    }
  }

  private log(level: LogLevel, message: string, options: LogOptions) {
    if (!dev && level === LogLevel.DEBUG) return;

    if (!Object.values(LogContext).includes(options.context)) {
      console.warn(`Invalid log context: ${options.context}`);
      return;
    }

    const formattedMessage = this.formatMessage(level, message, options);
    this.ensureGroupStarted(options.context);

    switch (level) {
      case LogLevel.ERROR:
        console.error(formattedMessage);
        if (options.data) console.error('▶', options.data);
        break;
      case LogLevel.WARN:
        console.warn(formattedMessage);
        if (options.data) console.warn('▶', options.data);
        break;
      case LogLevel.DEBUG:
        console.debug(formattedMessage);
        if (options.data) console.debug('▶', options.data);
        break;
      default:
        console.log(formattedMessage);
        if (options.data) console.log('▶', options.data);
    }
  }

  debug(message: string, options: LogOptions) {
    this.log(LogLevel.DEBUG, message, options);
  }

  info(message: string, options: LogOptions) {
    this.log(LogLevel.INFO, message, options);
  }

  warn(message: string, options: LogOptions) {
    this.log(LogLevel.WARN, message, options);
  }

  error(message: string, options: LogOptions) {
    this.log(LogLevel.ERROR, message, options);
  }

  // Méthode pour nettoyer les groupes (utile lors de la navigation)
  clearGroups() {
    this.activeGroups.forEach((active, context) => {
      if (active) {
        console.groupEnd();
        this.activeGroups.set(context, false);
      }
    });
  }
}

export const logger = new Logger(); 