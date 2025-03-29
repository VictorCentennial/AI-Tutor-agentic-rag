#!/bin/sh
set -e

# Create config.js with environment variables
cat > /usr/share/nginx/html/config.js << EOF
window.APP_CONFIG = {
    DEBUG_MODE: ${DEBUG_MODE:-false},
    SEMESTER_START_DATE: "${SEMESTER_START_DATE:-"2025-01-08"}",
    TOTAL_WEEKS: ${TOTAL_WEEKS:-14},
    API_URL: "${API_URL:-"http://127.0.0.1:5001"}"
};
EOF

echo "Generated config.js with environment variables"

# Execute CMD
exec "$@" 