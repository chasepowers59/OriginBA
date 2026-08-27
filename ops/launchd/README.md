# Portal services under launchd

API (8000) and web (3000) run as user launch agents — start at login, restart
on crash. Install:

    cp *.plist ~/Library/LaunchAgents/
    launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.origin.portal-api.plist
    launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.origin.portal-web.plist

After a `next build`, bounce the web service:
    launchctl kickstart -k gui/$(id -u)/com.origin.portal-web

The API plist carries the warehouse URLs (localhost, no secrets); per-tenant
env keys for real clients belong in the deployment environment, not here.
Logs: /tmp/portal-api.log|err, /tmp/portal-web.log|err.
