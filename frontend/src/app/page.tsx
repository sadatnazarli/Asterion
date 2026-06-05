import { redirect } from 'next/navigation'

// Default route -> Market Terminal. Rationale: the terminal opens on the market,
// like Bloomberg/Yahoo; portfolio intelligence lives one click away at /dashboard.
export default function Home() {
  redirect('/market')
}
