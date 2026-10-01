import { FallbackPanel } from "@/components/FallbackPanel";

export default function NotFound() {
  return (
    <FallbackPanel title="Page not found">
      This address does not match a page in the portal. The link may be old or mistyped.
    </FallbackPanel>
  );
}
