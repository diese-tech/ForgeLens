# Scope ForgeLens data by Discord guild

ForgeLens is multi-tenant by `guild_id`: each Discord server has isolated settings, seasons, players, matches, exports, and optional ledger configuration. External destinations such as Google Sheets, Google Drive, and OneDrive are server-configured outputs rather than the source of truth. This avoids a single league, owner, or API account becoming the global bottleneck.
