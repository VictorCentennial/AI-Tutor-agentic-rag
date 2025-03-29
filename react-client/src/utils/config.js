// Default configuration values
const defaultConfig = {
    DEBUG_MODE: false,
    SEMESTER_START_DATE: "2025-01-08",
    TOTAL_WEEKS: 14,
    API_URL: "http://127.0.0.1:5001"
};

// Get config for browser environment
export function useConfig() {
    // For browser environment
    if (typeof window !== 'undefined' && window.APP_CONFIG) {
        return window.APP_CONFIG;
    }

    // Fallback to default config
    return defaultConfig;
}

// For Node.js environment (used in Vite config)
export function getServerConfig() {
    // In Node.js environment, try to get from process.env
    // eslint-disable-next-line no-undef
    if (typeof process !== 'undefined' && process.env) {
        return {
            // eslint-disable-next-line no-undef
            DEBUG_MODE: process.env.DEBUG_MODE === 'true',
            // eslint-disable-next-line no-undef
            SEMESTER_START_DATE: process.env.SEMESTER_START_DATE || defaultConfig.SEMESTER_START_DATE,
            // eslint-disable-next-line no-undef
            TOTAL_WEEKS: parseInt(process.env.TOTAL_WEEKS || defaultConfig.TOTAL_WEEKS.toString(), 10),
            // eslint-disable-next-line no-undef
            API_URL: process.env.API_URL || defaultConfig.API_URL
        };
    }

    return defaultConfig;
}

// Default export for simpler imports
export default {
    useConfig,
    getServerConfig
}; 