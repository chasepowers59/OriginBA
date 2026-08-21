/** Open browser print dialog for a council-ready analytics pack (save as PDF). */
import { brandTitle } from "./brand";
export function printCouncilPack(title: string): void {
  const previous = document.title;
  document.title = brandTitle(title);
  window.print();
  window.setTimeout(() => {
    document.title = previous;
  }, 500);
}
