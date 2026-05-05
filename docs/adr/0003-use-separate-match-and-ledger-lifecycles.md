# Use separate match and ledger lifecycles

ForgeLens tracks match/stat status separately from ledger/betting status. Match state controls evidence, OCR, review, confirmation, official status, and exports; ledger state controls whether betting is disabled, open, closed, pending result, resolved, or voided. A ledger may only resolve after the related match is official, which prevents payouts from depending directly on unreviewed OCR or GodForge draft data.
