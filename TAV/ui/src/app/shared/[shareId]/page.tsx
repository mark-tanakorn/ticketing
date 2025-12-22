"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { forkSharedWorkflow, getSharedWorkflowPreview, type SharedWorkflowPreview } from "@/lib/editor";

export default function SharedWorkflowPage() {
  const params = useParams<{ shareId: string }>();
  const router = useRouter();
  const shareId = params?.shareId;

  const [loading, setLoading] = useState(true);
  const [forking, setForking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<SharedWorkflowPreview | null>(null);

  useEffect(() => {
    if (!shareId) return;
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await getSharedWorkflowPreview(shareId);
        if (!cancelled) setPreview(data);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || "Failed to load shared workflow");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [shareId]);

  return (
    <div
      className="min-h-screen flex items-center justify-center p-6"
      style={{ background: "var(--theme-background)", color: "var(--theme-text)" }}
    >
      <div
        className="w-full max-w-2xl rounded-lg border shadow-xl"
        style={{ background: "var(--theme-surface)", borderColor: "var(--theme-border)" }}
      >
        <div className="p-5 border-b" style={{ borderColor: "var(--theme-border)" }}>
          <h1 className="text-xl font-semibold">Shared Workflow</h1>
          <div className="text-sm mt-1" style={{ color: "var(--theme-text-muted)" }}>
            Share ID: <span className="font-mono">{shareId}</span>
          </div>
        </div>

        <div className="p-5 space-y-4">
          {loading ? (
            <div className="text-sm" style={{ color: "var(--theme-text-muted)" }}>
              Loading…
            </div>
          ) : error ? (
            <div className="text-sm" style={{ color: "var(--theme-danger)" }}>
              {error}
            </div>
          ) : preview ? (
            <>
              <div>
                <div className="text-lg font-semibold">{preview.name}</div>
                {preview.description ? (
                  <div className="text-sm mt-1" style={{ color: "var(--theme-text-secondary)" }}>
                    {preview.description}
                  </div>
                ) : null}
              </div>

              <div className="flex items-center gap-2 text-sm">
                <span
                  className="px-2 py-0.5 rounded border"
                  style={{ borderColor: "var(--theme-border)", color: "var(--theme-text-secondary)" }}
                >
                  Visibility: {preview.visibility}
                </span>
                {preview.tags?.length ? (
                  <span style={{ color: "var(--theme-text-muted)" }}>Tags: {preview.tags.join(", ")}</span>
                ) : null}
              </div>

              <div className="rounded p-3 text-sm" style={{ background: "var(--theme-surface-variant)" }}>
                <div className="font-medium">Sharing mode</div>
                <div className="mt-1" style={{ color: "var(--theme-text-muted)" }}>
                  {preview.share_mode === "open"
                    ? "This link is configured for synced collaboration (coming soon)."
                    : preview.share_mode === "choose"
                    ? "This link will let viewers choose between opening shared vs duplicating (coming soon)."
                    : "This link is configured as a copy (fork). Duplicating creates your own private version."}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                {(preview.share_mode === "open" || preview.share_mode === "choose") && (
                  <button
                    className="px-4 py-2 rounded border text-sm"
                    style={{
                      background: "var(--theme-surface-variant)",
                      color: "var(--theme-text-muted)",
                      borderColor: "var(--theme-border)",
                      cursor: "not-allowed",
                    }}
                    disabled
                    title="Collaboration mode is not implemented yet"
                  >
                    Open shared (soon)
                  </button>
                )}

                {(preview.share_mode !== "open") && (
                  <button
                  className="px-4 py-2 rounded text-sm text-white"
                  style={{ background: "var(--theme-primary)" }}
                  disabled={forking}
                  onClick={async () => {
                    if (!shareId) return;
                    try {
                      setForking(true);
                      const res = await forkSharedWorkflow(shareId);
                      router.push(`/editor-page?workflow=${res.workflow_id}`);
                    } catch (e: any) {
                      setError(e?.message || "Failed to duplicate workflow");
                    } finally {
                      setForking(false);
                    }
                  }}
                >
                  {forking ? "Duplicating…" : "Duplicate to my workspace"}
                  </button>
                )}
              </div>
            </>
          ) : (
            <div className="text-sm" style={{ color: "var(--theme-text-muted)" }}>
              Not found.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


