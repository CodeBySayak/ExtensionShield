/**
 * Secure Logger Utility
 * 
 * Prevents information leakage in production by gating console statements.
 * Only logs in development mode, except for errors which are always logged.
 */

const isDev = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;

/**
 * Development-only logger
 * Only logs in development mode to prevent information leakage
 */
export const logger = {
  /**
   * Log debug information (development only)
   */
  log: (...args) => {
    if (isDev) {
      console.log(...args);
    }
  },

  /**
   * Log warnings (development only)
   */
  warn: (...args) => {
    if (isDev) {
      console.warn(...args);
    }
  },

  /**
   * Log errors (development only for now; prod: no console output)
   */
  error: (...args) => {
    if (isDev) {
      console.error(...args);
    }
  },

  /**
   * Log info (development only)
   */
  info: (...args) => {
    if (isDev) {
      console.info(...args);
    }
  },

  /**
   * Log debug (development only)
   */
  debug: (...args) => {
    if (isDev) {
      console.debug(...args);
    }
  },

  /**
   * Check if logging is enabled
   */
  isEnabled: () => isDev,
  
  /**
   * Check if in production
   */
  isProduction: () => isProduction,
};

export default logger;

