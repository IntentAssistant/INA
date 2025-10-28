#!/bin/bash

# Copy this file to codesign_config.local.sh and replace placeholders
# with your private Apple Developer credentials. Keep the local file
# out of version control.

export CODESIGN_IDENTITY="Developer ID Application: __REPLACE_ME__"
export APPLE_ID="your.apple.id@example.com"
export APPLE_APP_PASSWORD="__REPLACE_ME__"
export APPLE_TEAM_ID="__REPLACE_ME__"
