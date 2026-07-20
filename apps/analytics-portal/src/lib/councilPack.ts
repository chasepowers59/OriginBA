/** Open browser print dialog for a council-ready analytics pack (save as PDF). */
export function printCouncilPack(title: string): void {
  const previous = document.title;
  document.title = `${title} | OriginBA Utility Insights`;
  window.print();
  window.setTimeout(() => {
    document.title = previous;
  }, 500);
}
