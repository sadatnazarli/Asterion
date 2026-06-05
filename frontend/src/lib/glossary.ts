// M8.11 — plain-English definitions for the guided beginner layer.
// One sentence each. No jargon explaining jargon. No buy/sell language.

export const GLOSSARY: Record<string, string> = {
  'valuation risk':
    'How expensive a stock is versus what the business actually earns — high means it is priced for perfection.',
  'expectations gap':
    'The growth the current price already assumes; a big gap means the market is expecting a lot to go right.',
  'thesis fragility':
    'How easily the reason you own a stock could break if things go only slightly worse than hoped.',
  rag: 'Retrieval — pulling the company’s own SEC filings into the analysis so claims are grounded in source text, not guessed.',
  memo: 'A written research note Asterion generates for a company from its filings.',
  cik: 'The SEC’s ID number for a company — how its official filings are looked up.',
  'sec facts': 'Official numbers pulled straight from a company’s SEC filings, not estimated.',
  'current value': 'What a position is worth right now at the latest price.',
  weight: 'How much of your whole portfolio this one position makes up.',
  'daily contribution': 'How many dollars this single position added to or removed from today’s change.',
  'live provider': 'Where the live price comes from (e.g. Finnhub); “live” means a real-time stream, not a delayed snapshot.',
  'core etf exposure': 'The share of your money in broad index funds (like VOO) that spread risk across many companies.',
  'ai / semiconductor exposure':
    'The share of your money tied to the AI and chip theme — these tend to move together if that theme sells off.',
  'total value': 'Everything you own added up at the latest prices.',
  'today p/l': 'How much your portfolio moved today, in dollars and percent (P/L = profit or loss).',
  'data quality': 'Whether Asterion has full data on a holding or is still missing some pieces.',
  'cost basis': 'What you originally paid for a position; without it, only today’s move can be shown, not total profit.',
}

// Convenience: definition lookup, case-insensitive.
export function define(term: string): string | undefined {
  return GLOSSARY[term.trim().toLowerCase()]
}
