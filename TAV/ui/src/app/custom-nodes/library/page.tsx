'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import 'highlight.js/styles/github-dark.css';
import hljs from 'highlight.js';

import {
  listMyCustomNodes,
  getMyCustomNode,
  updateMyCustomNodeCode,
  validateMyCustomNode,
  registerMyCustomNode,
  deleteMyCustomNode,
  type CustomNodeSummary,
  type CustomNodeDetail,
  type NodeValidationResponse,
} from '@/lib/custom-nodes';

export default function CustomNodesLibraryPage() {
  const router = useRouter();

  const [nodes, setNodes] = useState<CustomNodeSummary[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedNode, setSelectedNode] = useState<CustomNodeDetail | null>(null);
  const [codeDraft, setCodeDraft] = useState('');
  const [isLoadingNode, setIsLoadingNode] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);
  const [validation, setValidation] = useState<NodeValidationResponse | null>(null);
  const [search, setSearch] = useState('');

  const filteredNodes = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return nodes;
    return nodes.filter((n) => {
      const hay = `${n.node_type} ${n.display_name} ${n.category} ${n.description || ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [nodes, search]);

  const highlightedHtml = useMemo(() => {
    const code = codeDraft || '';
    try {
      return hljs.highlight(code, { language: 'python' }).value;
    } catch {
      try {
        return hljs.highlightAuto(code).value;
      } catch {
        // Very defensive: render plain text
        return code
          .replaceAll('&', '&amp;')
          .replaceAll('<', '&lt;')
          .replaceAll('>', '&gt;');
      }
    }
  }, [codeDraft]);

  async function loadList() {
    setIsLoadingList(true);
    try {
      const res = await listMyCustomNodes();
      setNodes(res.nodes || []);
      if (!selectedId && res.nodes?.length) {
        setSelectedId(res.nodes[0].id);
      }
    } finally {
      setIsLoadingList(false);
    }
  }

  async function loadNode(id: number) {
    setIsLoadingNode(true);
    setValidation(null);
    try {
      const n = await getMyCustomNode(id);
      setSelectedNode(n);
      setCodeDraft(n.code || '');
    } finally {
      setIsLoadingNode(false);
    }
  }

  useEffect(() => {
    loadList().catch((e) => alert(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedId == null) return;
    loadNode(selectedId).catch((e) => alert(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  async function handleSave() {
    if (!selectedNode) return;
    setIsSaving(true);
    try {
      const res = await updateMyCustomNodeCode(selectedNode.id, codeDraft);
      setSelectedNode(res.node);
      await loadList();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setIsSaving(false);
    }
  }

  async function handleValidate() {
    if (!selectedNode) return;
    setIsValidating(true);
    try {
      // validate the draft locally via existing /validate endpoint (which validates stored code),
      // so save first if draft differs.
      if (codeDraft !== selectedNode.code) {
        await handleSave();
      }
      const res = await validateMyCustomNode(selectedNode.id);
      setValidation(res);
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to validate');
    } finally {
      setIsValidating(false);
    }
  }

  async function handleRegister() {
    if (!selectedNode) return;
    setIsRegistering(true);
    try {
      if (codeDraft !== selectedNode.code) {
        await handleSave();
      }
      const res = await registerMyCustomNode(selectedNode.id);
      alert(res.message);
      await loadList();
      await loadNode(selectedNode.id);
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to register');
    } finally {
      setIsRegistering(false);
    }
  }

  async function handleDeleteNode(nodeId: number) {
    const node = nodes.find((n) => n.id === nodeId);
    const label = node ? `${node.display_name} (${node.node_type})` : `Node ${nodeId}`;
    const ok = confirm(`Delete custom node: ${label}?\n\nThis will remove the node file and unregister it.`);
    if (!ok) return;

    try {
      await deleteMyCustomNode(nodeId);
      // If we deleted the selected node, clear selection
      if (selectedId === nodeId) {
        setSelectedId(null);
        setSelectedNode(null);
        setCodeDraft('');
        setValidation(null);
      }
      await loadList();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed to delete');
    }
  }

  return (
    <div className="flex overflow-hidden h-full" style={{ background: 'var(--theme-background)' }}>
      {/* Left list */}
      <div
        className="w-80 flex flex-col border-r flex-shrink-0"
        style={{ background: 'var(--theme-card-bg)', borderColor: 'var(--theme-border)' }}
      >
        <div className="p-4 border-b" style={{ borderColor: 'var(--theme-border)' }}>
          <div className="flex items-center justify-between gap-2">
            <div className="text-sm font-semibold" style={{ color: 'var(--theme-text)' }}>
              My Nodes
            </div>
            <button
              type="button"
              onClick={() => router.push('/builder')}
              className="text-xs px-2 py-1 rounded border cursor-pointer hover:opacity-90 transition-opacity"
              style={{
                borderColor: 'var(--theme-border)',
                background: 'var(--theme-card-bg-secondary)',
                color: 'var(--theme-text-muted)',
              }}
            >
              Back to Chat
            </button>
          </div>

          <div className="mt-3">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search nodes..."
              className="w-full px-3 py-2 rounded-md border text-sm"
              style={{
                background: 'var(--theme-input-bg)',
                borderColor: 'var(--theme-border)',
                color: 'var(--theme-text)',
              }}
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {isLoadingList ? (
            <div className="p-3 text-sm" style={{ color: 'var(--theme-text-muted)' }}>
              Loading…
            </div>
          ) : filteredNodes.length ? (
            filteredNodes.map((n) => (
              <div
                key={n.id}
                className="w-full p-3 rounded-lg border mb-2 group relative"
                style={{
                  borderColor: selectedId === n.id ? 'var(--theme-border-primary)' : 'var(--theme-border)',
                  background: selectedId === n.id ? 'var(--theme-card-bg-secondary)' : 'transparent',
                  color: 'var(--theme-text)',
                }}
              >
                <button
                  type="button"
                  onClick={() => setSelectedId(n.id)}
                  className="w-full text-left"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-semibold text-sm truncate pr-10">{n.display_name}</div>
                    <div className="text-xs" style={{ color: 'var(--theme-text-muted)' }}>
                      {n.is_registered ? 'registered' : 'draft'}
                    </div>
                  </div>
                  <div className="text-xs mt-1 truncate" style={{ color: 'var(--theme-text-muted)' }}>
                    {n.node_type} • {n.category}
                  </div>
                </button>

                {/* Delete button (like chat delete) */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteNode(n.id);
                  }}
                  className="absolute top-2 right-2 p-2 rounded-md border opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{
                    borderColor: 'var(--theme-border)',
                    background: 'var(--theme-card-bg-secondary)',
                    color: 'var(--theme-text-muted)',
                  }}
                  title="Delete node"
                >
                  <i className="fa-solid fa-trash"></i>
                </button>
              </div>
            ))
          ) : (
            <div className="p-3 text-sm" style={{ color: 'var(--theme-text-muted)' }}>
              No nodes found.
            </div>
          )}
        </div>
      </div>

      {/* Right editor */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="p-4 border-b flex items-center justify-between gap-3" style={{ borderColor: 'var(--theme-border)' }}>
          <div className="min-w-0">
            <div className="text-sm font-semibold truncate" style={{ color: 'var(--theme-text)' }}>
              {selectedNode ? `${selectedNode.display_name} (${selectedNode.node_type})` : 'Select a node'}
            </div>
            {selectedNode ? (
              <div className="text-xs truncate" style={{ color: 'var(--theme-text-muted)' }}>
                {selectedNode.file_path || 'Not written to disk yet'} • Updated {new Date(selectedNode.updated_at).toLocaleString()}
              </div>
            ) : null}
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              type="button"
              onClick={() => loadList().catch((e) => alert(e.message))}
              className="text-xs px-2 py-1 rounded border"
              style={{
                borderColor: 'var(--theme-border)',
                background: 'var(--theme-card-bg-secondary)',
                color: 'var(--theme-text-muted)',
              }}
              disabled={isLoadingList}
            >
              Refresh
            </button>
            <button
              type="button"
              onClick={handleValidate}
              disabled={!selectedNode || isValidating || isSaving || isLoadingNode}
              className="text-xs px-2 py-1 rounded border"
              style={{
                borderColor: 'var(--theme-border)',
                background: 'var(--theme-card-bg-secondary)',
                color: 'var(--theme-text-muted)',
              }}
            >
              {isValidating ? 'Validating…' : 'Validate'}
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={!selectedNode || isSaving || isLoadingNode}
              className="text-xs px-2 py-1 rounded border"
              style={{
                borderColor: 'var(--theme-border)',
                background: 'var(--theme-card-bg-secondary)',
                color: 'var(--theme-text-muted)',
              }}
            >
              {isSaving ? 'Saving…' : 'Save Draft'}
            </button>
            <button
              type="button"
              onClick={handleRegister}
              disabled={!selectedNode || isRegistering || isSaving || isLoadingNode}
              className="text-xs px-2 py-1 rounded border"
              style={{
                borderColor: 'var(--theme-border-primary)',
                background: 'var(--theme-button-primary)',
                color: 'white',
              }}
            >
              {isRegistering ? 'Registering…' : 'Register'}
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-hidden flex">
          <div className="flex-1 min-w-0 p-4 overflow-hidden">
            {isLoadingNode ? (
              <div className="text-sm" style={{ color: 'var(--theme-text-muted)' }}>
                Loading node…
              </div>
            ) : selectedNode ? (
              <div
                className="code-editor w-full h-full rounded-lg border overflow-hidden"
                style={{ borderColor: 'var(--theme-border)', background: '#1e1e1e' }}
              >
                <div className="relative w-full h-full">
                  {/* Highlighted layer */}
                  <pre
                    id="highlight-layer"
                    className="absolute inset-0 p-3 overflow-auto"
                    style={{
                      margin: 0,
                      // Fallback foreground in case a token isn't styled by hljs theme
                      color: '#c9d1d9',
                      lineHeight: 1.5,
                      fontSize: 12,
                      fontFamily:
                        'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                      whiteSpace: 'pre',
                      tabSize: 2 as any,
                    }}
                  >
                    <code
                      className="hljs language-python"
                      style={{
                        // hljs themes often add padding/background on code.hljs; remove so it aligns with textarea.
                        padding: 0,
                        background: 'transparent',
                        display: 'block',
                      }}
                      dangerouslySetInnerHTML={{ __html: highlightedHtml + '\n' }}
                    />
                  </pre>

                  {/* Editable layer */}
                  <textarea
                    value={codeDraft}
                    onChange={(e) => setCodeDraft(e.target.value)}
                    onScroll={(e) => {
                      const ta = e.currentTarget;
                      const hl = ta.parentElement?.querySelector<HTMLDivElement>('#highlight-layer');
                      if (hl) {
                        hl.scrollTop = ta.scrollTop;
                        hl.scrollLeft = ta.scrollLeft;
                      }
                    }}
                    spellCheck={false}
                    className="absolute inset-0 w-full h-full p-3 font-mono text-xs resize-none outline-none"
                    style={{
                      background: 'transparent',
                      // Hide textarea text so the highlighted layer shows through.
                      color: 'transparent',
                      caretColor: 'white',
                      lineHeight: 1.5,
                      fontSize: 12,
                      fontFamily:
                        'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                      whiteSpace: 'pre',
                      tabSize: 2 as any,
                      // Keep selection usable
                      WebkitTextFillColor: 'transparent' as any,
                    }}
                  />
                </div>
                <style jsx>{`
                  .code-editor code.hljs {
                    padding: 0 !important;
                    background: transparent !important;
                  }
                  .code-editor textarea::selection {
                    background: rgba(56, 139, 253, 0.35);
                  }
                `}</style>
              </div>
            ) : (
              <div className="text-sm" style={{ color: 'var(--theme-text-muted)' }}>
                Pick a node from the left.
              </div>
            )}
          </div>

          <div className="w-[360px] border-l p-4 overflow-y-auto" style={{ borderColor: 'var(--theme-border)' }}>
            <div className="text-sm font-semibold mb-2" style={{ color: 'var(--theme-text)' }}>
              Validation
            </div>
            {validation ? (
              <>
                <div className="text-sm mb-3" style={{ color: validation.valid ? '#22c55e' : '#ef4444' }}>
                  {validation.valid ? 'Valid' : 'Invalid'}
                </div>

                {validation.errors?.length ? (
                  <div className="mb-3">
                    <div className="text-xs font-semibold mb-1" style={{ color: 'var(--theme-text)' }}>
                      Errors
                    </div>
                    <ul className="text-xs space-y-1" style={{ color: 'var(--theme-text-muted)' }}>
                      {validation.errors.map((e, idx) => (
                        <li key={idx}>{e.message}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {validation.warnings?.length ? (
                  <div className="mb-3">
                    <div className="text-xs font-semibold mb-1" style={{ color: 'var(--theme-text)' }}>
                      Warnings
                    </div>
                    <ul className="text-xs space-y-1" style={{ color: 'var(--theme-text-muted)' }}>
                      {validation.warnings.map((w, idx) => (
                        <li key={idx}>{w.message}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </>
            ) : (
              <div className="text-sm" style={{ color: 'var(--theme-text-muted)' }}>
                Click Validate to check the node.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


