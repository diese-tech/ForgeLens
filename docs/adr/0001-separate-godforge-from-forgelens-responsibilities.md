# Separate GodForge from ForgeLens responsibilities

GodForge owns live match orchestration: sessions, randomization, draft flow, picks, bans, and optional Draft JSON output. ForgeLens owns evidence intake, OCR parsing, normalized stat records, exports, and optional ledger workflows. This keeps the live match bot small and reliable while allowing the stat bot to become the heavier analytics and reporting system.
