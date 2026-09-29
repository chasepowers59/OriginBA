"use client";

import { useEffect, useState, type ReactNode } from "react";
import { fetchLetter, fetchLetterPdf } from "@/lib/api";
import { formatDateTime, saveBlob } from "@/lib/format";
import {
  formatAmount,
  letterErrorMessage,
  statusLabel,
  type LetterDetail,
  type LetterPdf,
  type LetterSummary,
} from "@/lib/letters";

export type PaneTab = "letter" | "data";

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-edge-subtle py-1.5 last:border-0">
      <span className="text-fg-muted">{label}</span>
      <span className="text-right text-heading">{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="glass-panel-subtle p-4">
      <h3 className="mb-2 text-sm font-semibold text-heading">{title}</h3>
      <div className="text-sm">{children}</div>
    </section>
  );
}

/**
 * One letter: its PDF (fetched with the signed-in headers and shown through an object URL) and
 * the data it was composed from, so a reviewer checks the letter against the process rather than
 * trusting it. The data is fetched only when its tab is opened: each read is audited as a preview.
 */
export function LetterDetailPane({ letter, tab, onTab }: { letter: LetterSummary; tab: PaneTab; onTab: (t: PaneTab) => void }) {
  const id = letter.letter_id;
  const [pdf, setPdf] = useState<{ url: string; data: LetterPdf } | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [detail, setDetail] = useState<LetterDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    let url: string | null = null;
    fetchLetterPdf(id)
      .then((data) => {
        if (!live) return;
        url = URL.createObjectURL(data.blob);
        setPdf({ url, data });
      })
      .catch((e) => live && setPdfError(letterErrorMessage(e)));
    return () => {
      live = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [id]);

  useEffect(() => {
    if (tab !== "data" || detail) return;
    let live = true;
    setDetailError(null);
    fetchLetter(id)
      .then((d) => live && setDetail(d))
      .catch((e) => live && setDetailError(letterErrorMessage(e)));
    return () => {
      live = false;
    };
  }, [id, tab, detail]);

  return (
    <div className="flex flex-col">
      <div className="flex items-start gap-3 border-b border-edge-subtle px-4 py-3">
        <div className="min-w-0">
          <h2 className="truncate font-semibold text-heading">{letter.kind_label}</h2>
          <p className="truncate text-xs text-fg-muted">
            {formatDateTime(letter.letter_date)} · Account {letter.account_id} · {id}
          </p>
        </div>
        <div className="ml-auto flex shrink-0 items-center gap-1.5">
          {(["letter", "data"] as const).map((t) => (
            <button key={t} type="button" aria-pressed={tab === t} onClick={() => onTab(t)}
              className={`chip ${tab === t ? "chip-active" : ""}`}>
              {t === "letter" ? "Letter" : "Data behind it"}
            </button>
          ))}
          <button type="button" disabled={!pdf} onClick={() => pdf && saveBlob(pdf.data.blob, `${id}.pdf`)}
            className="btn-primary ml-1.5 px-3 py-1.5 text-xs">
            Download PDF
          </button>
        </div>
      </div>

      {tab === "letter" ? (
        pdfError ? (
          <p role="alert" className="p-6 text-sm text-heading">{pdfError}</p>
        ) : pdf ? (
          <>
            {pdf.data.fontNote ? <p className="bg-warn-bg px-4 py-2 text-xs text-warn">{pdf.data.fontNote}</p> : null}
            <iframe title={`Letter ${id}`} src={pdf.url} className="h-[70vh] w-full" />
          </>
        ) : (
          <div role="status" aria-label="Preparing the letter" className="loading-shimmer m-4 h-[60vh] rounded-xl" />
        )
      ) : (
        <div className="max-h-[75vh] space-y-4 overflow-y-auto p-4">
          {detailError ? <p role="alert" className="text-sm text-heading">{detailError}</p> : null}
          {!detail && !detailError ? <div role="status" aria-label="Loading the letter's data" className="loading-shimmer h-48 rounded-xl" /> : null}
          {detail ? <LetterData detail={detail} /> : null}
        </div>
      )}
    </div>
  );
}

function LetterData({ detail }: { detail: LetterDetail }) {
  const { letter, recipient, composed, process: p, returned_payment: nsf, late_fee: fee } = detail;
  return (
    <>
      <Section title="Sent to">
        <p className="whitespace-pre-line text-heading">{recipient.address_lines.join("\n")}</p>
        <div className="mt-2">
          <Row label="Account" value={letter.account_id} />
          <Row label="Person ID" value={recipient.person_id || "—"} />
        </div>
      </Section>

      <Section title="This letter">
        <Row label="Type" value={letter.kind_label} />
        <Row label="Letter date" value={formatDateTime(letter.letter_date)} />
        <Row label="Created" value={formatDateTime(detail.created_at)} />
        <Row label="Status" value={detail.printed_at ? `Printed ${formatDateTime(detail.printed_at)}` : statusLabel(false)} />
        <Row label="Copies" value={letter.copies} />
        <Row label={composed.glance_label} value={<strong>{formatAmount(composed.glance_amount)}</strong>} />
        <Row label="Account balance" value={formatAmount(detail.account_balance)} />
        <Row label="Customer contact ID" value={detail.contact_id ?? "—"} />
        <Row label="Letter template" value={letter.template_code || "—"} />
      </Section>

      {p ? (
        <Section title={`${p.process_type} process`}>
          <Row label="Process ID" value={p.process_id} />
          <Row label="Past due amount" value={formatAmount(p.arrears_amount)} />
          <Row label="Past due as of" value={formatDateTime(p.arrears_as_of)} />
          <Row label="Next action"
            value={p.next_action_on ? `${formatDateTime(p.next_action_on)} · ${p.next_action_type}` : "None scheduled"} />
          {p.cut_scheduled_on ? <Row label="Disconnection scheduled" value={formatDateTime(p.cut_scheduled_on)} /> : null}
          {p.cut_completed_on ? <Row label="Disconnected on" value={<strong>{formatDateTime(p.cut_completed_on)}</strong>} /> : null}
          {p.services.length ? (
            <table className="mt-3 w-full text-xs">
              <thead>
                <tr className="border-b border-edge-subtle text-left text-fg-muted">
                  <th scope="col" className="py-1 font-medium">Service agreement</th>
                  <th scope="col" className="font-medium">Service</th>
                  <th scope="col" className="font-medium">Premise</th>
                  <th scope="col" className="text-right font-medium">Amount</th>
                </tr>
              </thead>
              <tbody>
                {p.services.map((s) => (
                  <tr key={s.sa_id} className="border-b border-edge-subtle text-heading last:border-0">
                    <td className="py-1 tabular-nums">{s.sa_id}</td>
                    <td>{s.service_type}</td>
                    <td>{s.premise_address}</td>
                    <td className="text-right tabular-nums">{formatAmount(s.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </Section>
      ) : null}

      {nsf ? (
        <Section title="Returned payment">
          <Row label="Adjustment ID" value={nsf.adjustment_id} />
          <Row label="Payment" value={`${formatAmount(nsf.payment_amount)} ${nsf.tender_type}`.trim()} />
          <Row label="Payment date" value={formatDateTime(nsf.payment_date)} />
          <Row label="Fee charged" value={formatAmount(nsf.fee_amount)} />
        </Section>
      ) : null}

      {fee ? (
        <Section title="Late payment charge">
          <Row label="Adjustment ID" value={fee.adjustment_id} />
          <Row label="Amount" value={formatAmount(fee.amount)} />
          <Row label="Charged on" value={formatDateTime(fee.charged_on)} />
          <Row label="Service" value={[fee.service_type, fee.premise_address].filter(Boolean).join(" · ")} />
        </Section>
      ) : null}

      <Section title="The words on the letter">
        <p className="font-semibold text-heading">{composed.subject}</p>
        {composed.paragraphs.map((text, i) => <p key={i} className="mt-2 text-fg">{text}</p>)}
        {composed.callout ? <p className="tint-panel mt-3 rounded-lg px-3 py-2 font-semibold text-heading">{composed.callout}</p> : null}
        {detail.body ? <p className="mt-3 text-fg-muted">Note on the customer contact: {detail.body}</p> : null}
      </Section>
    </>
  );
}
