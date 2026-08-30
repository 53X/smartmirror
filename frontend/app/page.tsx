import { redirect } from "next/navigation";

/**
 * Customer entry: floor attract screen, then tap into consent.
 * Staff operators bookmark `/staff/login` — not the primary landing path.
 */
export default function HomePage() {
  redirect("/kiosk/attract");
}
