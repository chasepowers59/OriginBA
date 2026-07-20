/** Open browser print dialog for snapshot lineage / join-path documentation (save as PDF). */
export function printLineagePack(title: string): void {
  const root = document.getElementById("lineage-pack-export");
  if (!root) return;
  root.classList.add("printing-lineage");
  const previous = document.title;
  document.title = `${title} | Data Model Lineage`;
  window.print();
  window.setTimeout(() => {
    root.classList.remove("printing-lineage");
    document.title = previous;
  }, 500);
}
