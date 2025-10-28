#!/bin/bash

# ======================================================
# Code Signing Configuration Loader for INA App
# ======================================================
# This script intentionally does not store credentials.
# Supply private values via an untracked file (default:
# codesign_config.local.sh) or environment variables
# before sourcing this loader.
# ======================================================

unset INA_CODESIGN_READY

CONFIG_SOURCE="${INA_CODESIGN_CONFIG:-codesign_config.local.sh}"
PLACEHOLDER_VALUE="__REPLACE_ME__"

if [ -f "$CONFIG_SOURCE" ]; then
    echo "🔐 Loading code signing credentials from $CONFIG_SOURCE"
    # shellcheck disable=SC1090
    source "$CONFIG_SOURCE"
else
    echo "⚠️  Code signing credentials file not found: $CONFIG_SOURCE"
    echo "    Create one (e.g. copy codesign_config.example.sh) with your private values."
fi

missing_vars=()

check_var() {
    local var_name="$1"
    local guidance="$2"
    local value="${!var_name:-}"

    if [ -z "$value" ] || [ "$value" = "$PLACEHOLDER_VALUE" ]; then
        missing_vars+=("$var_name:$guidance")
    fi
}

check_var "CODESIGN_IDENTITY" "Developer ID Application certificate name or SHA-1 hash."
check_var "APPLE_ID" "Apple Developer Program login email."
check_var "APPLE_APP_PASSWORD" "App-specific password generated at appleid.apple.com."
check_var "APPLE_TEAM_ID" "10-character Apple Developer Team ID."

if [ "${#missing_vars[@]}" -gt 0 ]; then
    echo "❌ Missing code signing credentials:"
    for item in "${missing_vars[@]}"; do
        local var_name="${item%%:*}"
        local guidance="${item#*:}"
        echo "   • $var_name → $guidance"
    done
    echo "    Update $CONFIG_SOURCE (or export the variables) and rerun."
    export INA_CODESIGN_READY=false
    return 0
fi

export CODESIGN_IDENTITY APPLE_ID APPLE_APP_PASSWORD APPLE_TEAM_ID
export INA_CODESIGN_READY=true

echo "✅ Code signing credentials ready."
echo "   Identity: ${CODESIGN_IDENTITY}"
echo "   Team ID: ${APPLE_TEAM_ID}"

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    return 0
fi

exit 0
