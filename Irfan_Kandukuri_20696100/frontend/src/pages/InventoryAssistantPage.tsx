import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { api, apiError } from "../services/api";
import { getMCPHistory, queryInventoryAssistant, queryInventoryAgent, queryMCPChat, runMultiAgentAnalysis } from "../services/rag";
import type { AgentQueryResponse, MCPChatResponse, MultiAgentAnalysisResponse, Product, RagSource } from "../types";

const suggestedQuestions = [
  "What is reorder point?",
  "When should a low stock alert be resolved?",
  "What happens when a PO is marked as received?",
  "What is the SKU format?",
];

function sourceLabel(source: RagSource): string {
  const parts = [source.source];
  if (source.chunk_index) {
    parts.push(`Chunk ${source.chunk_index}`);
  }
  if (source.section) {
    parts.push(source.section);
  }
    return parts.join(" | ");
}

type AssistantMode = "knowledge" | "agent" | "mcp" | "multi-agent";

function modeBadgeLabel(mode: AssistantMode): string {
  if (mode === "agent") return "Phase 3 Agent";
  if (mode === "mcp") return "Phase 4 MCP Chat";
  if (mode === "multi-agent") return "Phase 5 Multi-Agent";
  return "Phase 2 RAG";
}

function submitButtonLabel(loading: boolean, mode: AssistantMode): string {
  if (!loading) return mode === "multi-agent" ? "Run Analysis" : "Ask";
  if (mode === "mcp") return "Working...";
  if (mode === "multi-agent") return "Analyzing...";
  return "Searching...";
}

function ModeRulesList({ mode }: Readonly<{ mode: AssistantMode }>) {
  return (
    <>
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">{mode === "agent" ? "Tool routing" : "Grounding rules"}</p>
      <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-200">
        {mode === "agent" ? <li>Agent Mode selects existing inventory APIs and the Phase 2 policy search.</li> : null}
        {mode === "mcp" ? <li>MCP Chat executes six inventory tools and keeps the last ten messages in this session.</li> : null}
        {mode === "knowledge" ? <li>Knowledge Mode answers from the inventory manual through ChromaDB retrieval.</li> : null}
        {mode === "multi-agent" ? (
          <li>Multi-Agent Mode runs a LangGraph pipeline: demand forecast, reorder recommendation, supplier quote, and audit report.</li>
        ) : null}
        <li>Responses remain local and use the existing Phase 1 and Phase 2 services.</li>
      </ul>
    </>
  );
}

function riskBadgeClass(risk: string): string {
  if (risk === "high") return "bg-red-100 text-red-700";
  if (risk === "medium") return "bg-amber-100 text-amber-800";
  if (risk === "low") return "bg-emerald-100 text-emerald-800";
  return "bg-slate-100 text-slate-600";
}

const PRODUCT_CATEGORIES = ["grocery", "electronics", "household", "personal_care", "clothing"];

function categoryLabel(category: string): string {
  if (category === "personal_care") return "Personal Care";
  return category.charAt(0).toUpperCase() + category.slice(1);
}

function categoryBadgeClass(category: string): string {
  switch (category) {
    case "grocery":
      return "bg-emerald-100 text-emerald-800";
    case "electronics":
      return "bg-blue-100 text-blue-800";
    case "household":
      return "bg-amber-100 text-amber-800";
    case "personal_care":
      return "bg-pink-100 text-pink-800";
    case "clothing":
      return "bg-purple-100 text-purple-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

function urgencyBadgeClass(urgency: string): string {
  if (urgency === "immediate") return "bg-red-100 text-red-700";
  if (urgency === "within_3_days") return "bg-amber-100 text-amber-800";
  if (urgency === "within_week") return "bg-blue-100 text-blue-800";
  return "bg-emerald-100 text-emerald-800";
}

function ProductSelector({
  products,
  loading,
  error,
  selectedProductId,
  onSelect,
  search,
  onSearchChange,
  categoryFilter,
  onCategoryChange,
}: Readonly<{
  products: Product[];
  loading: boolean;
  error: string | null;
  selectedProductId: number | null;
  onSelect: (productId: number) => void;
  search: string;
  onSearchChange: (value: string) => void;
  categoryFilter: string;
  onCategoryChange: (value: string) => void;
}>) {
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return products.filter((product) => {
      const matchesCategory = !categoryFilter || product.category === categoryFilter;
      const matchesSearch = !query || product.name.toLowerCase().includes(query) || product.sku.toLowerCase().includes(query);
      return matchesCategory && matchesSearch;
    });
  }, [products, search, categoryFilter]);

  const selected = products.find((product) => product.id === selectedProductId) ?? null;

  return (
    <div className="space-y-3">
      <label className="block text-sm font-semibold text-slate-300" htmlFor="product-search">
        Select Product
      </label>
      <div className="flex flex-wrap gap-2">
        <input
          id="product-search"
          className="input flex-1 min-w-[220px]"
          placeholder="Search by product name or SKU..."
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
        />
        <select className="input w-48" value={categoryFilter} onChange={(event) => onCategoryChange(event.target.value)}>
          <option value="">All Categories</option>
          {PRODUCT_CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {categoryLabel(category)}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <p className="rounded-xl border border-dashed border-white/15 px-4 py-3 text-sm text-slate-400">Loading products...</p>
      ) : error ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      ) : filtered.length === 0 ? (
        <p className="rounded-xl border border-dashed border-white/15 px-4 py-3 text-sm text-slate-400">No products available</p>
      ) : (
        <div className="max-h-64 divide-y divide-white/10 overflow-y-auto rounded-xl border border-white/10">
          {filtered.map((product) => (
            <button
              key={product.id}
              type="button"
              onClick={() => onSelect(product.id)}
              className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm transition ${
                product.id === selectedProductId ? "bg-cyan-400/10 text-white" : "text-slate-300 hover:bg-white/[.04]"
              }`}
            >
              <span className="truncate">
                {product.name} <span className="text-xs text-slate-500">({product.sku})</span>
              </span>
              <span className={`badge shrink-0 ${categoryBadgeClass(product.category)}`}>{categoryLabel(product.category)}</span>
            </button>
          ))}
        </div>
      )}

      {selected ? (
        <p className="text-xs text-slate-400">
          Selected: <span className="font-semibold text-slate-200">{selected.name}</span> ({selected.sku})
        </p>
      ) : null}
    </div>
  );
}

function MultiAgentDashboard({ result }: Readonly<{ result: MultiAgentAnalysisResponse | null }>) {
  if (!result) {
    return (
      <section className="card">
        <h2 className="font-heading text-xl font-semibold">Inventory Analysis Dashboard</h2>
        <p className="mt-3 text-sm leading-6 text-slate-500">Select a product and run analysis to see the multi-agent report.</p>
      </section>
    );
  }

  const { demand_forecast: forecast, reorder_recommendation: reorder, supplier_quote: quote } = result;

  return (
    <section className="card space-y-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-heading text-xl font-semibold">Inventory Analysis Dashboard</h2>
        <span className="badge bg-indigo-100 text-indigo-800">Status: {result.analysis_status}</span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <span aria-hidden="true">📈</span> Demand Forecast
          </p>
          <p className="mt-2 text-sm text-slate-700">Avg daily demand: {forecast.avg_daily_demand}</p>
          <p className="text-sm text-slate-700">Trend: {forecast.demand_trend}</p>
          <p className="text-sm text-slate-700">Days of stock remaining: {forecast.days_of_stock_remaining}</p>
          <span className={`badge mt-2 inline-block ${riskBadgeClass(forecast.stockout_risk)}`}>Risk: {forecast.stockout_risk}</span>
          <p className="mt-2 text-xs text-slate-500">{forecast.forecast_notes}</p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <span aria-hidden="true">🛒</span> Reorder Recommendation
          </p>
          <span className={`badge mt-2 inline-block ${reorder.reorder_required ? "bg-red-100 text-red-700" : "bg-emerald-100 text-emerald-800"}`}>
            {reorder.reorder_required ? "Reorder Required" : "No Reorder Needed"}
          </span>
          <p className="mt-2 text-sm text-slate-700">Recommended quantity: {reorder.recommended_quantity}</p>
          <span className={`badge mt-1 inline-block ${urgencyBadgeClass(reorder.urgency)}`}>Urgency: {reorder.urgency}</span>
          <p className="mt-2 text-xs text-slate-500">{reorder.reason}</p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <span aria-hidden="true">🚚</span> Supplier Quote
          </p>
          <p className="mt-2 text-sm text-slate-700">Supplier: {quote.supplier_id ?? "N/A"}</p>
          <p className="text-sm text-slate-700">Unit cost: {quote.quoted_unit_cost.toFixed(2)}</p>
          <p className="text-sm text-slate-700">Total cost: {quote.total_order_cost.toFixed(2)}</p>
          <p className="text-sm text-slate-700">Lead time: {quote.estimated_lead_time_days} days</p>
          <p className="mt-2 text-xs text-slate-500">{quote.quote_notes}</p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <span aria-hidden="true">📋</span> Inventory Audit
          </p>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{result.audit_report}</p>
        </article>
      </div>

      {result.errors.length > 0 ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
          {result.errors.join("; ")}
        </div>
      ) : null}
    </section>
  );
}

function AnswerPanel({
  loading,
  answer,
  agentResult,
  mcpResult,
}: Readonly<{
  loading: boolean;
  answer: string;
  agentResult: AgentQueryResponse | null;
  mcpResult: MCPChatResponse | null;
}>) {
  return (
    <section className="card min-h-[220px]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-heading text-xl font-semibold">Answer</h2>
        {loading ? <span className="badge bg-amber-100 text-amber-800">Retrieving context...</span> : null}
      </div>
      {answer ? (
        <div className="whitespace-pre-wrap rounded-2xl border border-white/10 bg-white/[.03] p-4 text-sm leading-7 text-slate-300">{answer}</div>
      ) : (
        <p className="text-sm leading-7 text-slate-500">Ask a question to see a grounded answer from the inventory manual.</p>
      )}
      {agentResult ? (
        <div className="mt-5 space-y-2 border-t border-slate-200 pt-4 text-xs text-slate-500">
          <p><strong>Tools used:</strong> {agentResult.tools_used.join(", ") || "None"}</p>
          <p><strong>Reasoning:</strong> {agentResult.reasoning}</p>
        </div>
      ) : null}
      {mcpResult ? (
        <div className="mt-5 space-y-3 border-t border-slate-200 pt-4 text-xs text-slate-500">
          <p><strong>Session:</strong> {mcpResult.session_id}</p>
        </div>
      ) : null}
    </section>
  );
}

function chatSenderLabel(role: string): string {
  return role === "user" ? "You" : "Copilot";
}

function chatTimestampLabel(timestamp: string | undefined): string {
  if (!timestamp) return "now";
  return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function McpConversation({ mcpResult }: Readonly<{ mcpResult: MCPChatResponse | null }>) {
  if (!mcpResult?.history.length) {
    return (
      <div className="rounded-2xl border border-dashed border-white/15 p-6 text-center text-sm text-slate-400">
        Ask for a dashboard, low-stock report, product, supplier, purchase order, or stock update.
      </div>
    );
  }
  return (
    <>
      {mcpResult.history.map((message, index) => (
        <div key={`${message.timestamp ?? "message"}-${index}`} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
          <article className={`max-w-[88%] rounded-2xl px-4 py-3 ${message.role === "user" ? "bg-cyan-400 text-slate-950" : "border border-white/10 bg-white/[.06] text-slate-200"}`}>
            <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
            <p className={`mt-2 text-[10px] ${message.role === "user" ? "text-slate-700" : "text-slate-500"}`}>
              {chatSenderLabel(message.role)} · {chatTimestampLabel(message.timestamp)}
            </p>
          </article>
        </div>
      ))}
    </>
  );
}

function McpToolTraces({ mcpResult }: Readonly<{ mcpResult: MCPChatResponse | null }>) {
  if (!mcpResult?.tool_traces.length) return null;
  return (
    <div className="mt-5 grid gap-3 border-t border-white/10 pt-4 sm:grid-cols-2">
      {mcpResult.tool_traces.map((trace, index) => (
        <article key={`${trace.tool}-${index}`} className="rounded-xl border border-cyan-400/20 bg-cyan-400/[.06] p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-semibold text-cyan-200">{trace.tool}</p>
            <span className="text-[10px] text-emerald-300">Completed</span>
          </div>
          <pre className="mt-2 max-h-24 overflow-auto whitespace-pre-wrap text-[11px] text-slate-400">{typeof trace.result === "string" ? trace.result : JSON.stringify(trace.result, null, 2)}</pre>
        </article>
      ))}
    </div>
  );
}

function McpChatPanel({
  mcpResult,
  conversationRef,
}: Readonly<{
  mcpResult: MCPChatResponse | null;
  conversationRef: React.RefObject<HTMLDivElement>;
}>) {
  return (
    <section className="card flex min-h-[420px] flex-col border-cyan-200/40 bg-slate-950 text-slate-100 lg:col-span-2">
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">Operations workspace</p>
          <h2 className="mt-1 font-heading text-xl font-semibold text-white">Inventory Copilot</h2>
        </div>
        <span className="badge bg-emerald-400/10 text-emerald-300">Session active</span>
      </div>
      <div ref={conversationRef} className="mt-5 min-h-0 flex-1 space-y-5 overflow-y-auto pr-2">
        <McpConversation mcpResult={mcpResult} />
      </div>
      <McpToolTraces mcpResult={mcpResult} />
    </section>
  );
}

export function InventoryAssistantPage() {
  const [mode, setMode] = useState<AssistantMode>("knowledge");
  const [question, setQuestion] = useState("What is reorder point?");
  const [products, setProducts] = useState<Product[]>([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productsError, setProductsError] = useState<string | null>(null);
  const [productSearch, setProductSearch] = useState("");
  const [productCategoryFilter, setProductCategoryFilter] = useState("");
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [answer, setAnswer] = useState<string>("");
  const [sources, setSources] = useState<RagSource[]>([]);
  const [agentResult, setAgentResult] = useState<AgentQueryResponse | null>(null);
  const [mcpResult, setMcpResult] = useState<MCPChatResponse | null>(null);
  const [multiAgentResult, setMultiAgentResult] = useState<MultiAgentAnalysisResponse | null>(null);
  const [sessionId] = useState(() => window.localStorage.getItem("poc07-mcp-session") ?? `session-${Date.now()}`);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const conversationRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    window.localStorage.setItem("poc07-mcp-session", sessionId);
  }, [sessionId]);

  useEffect(() => {
    conversationRef.current?.scrollTo({ top: conversationRef.current.scrollHeight, behavior: "smooth" });
  }, [mcpResult?.history.length]);

  useEffect(() => {
    if (mode !== "mcp" || mcpResult) return;
    void getMCPHistory(sessionId).then(setMcpResult).catch(() => undefined);
  }, [mode, mcpResult, sessionId]);

  useEffect(() => {
    if (mode !== "multi-agent" || products.length > 0 || productsLoading) return;
    setProductsLoading(true);
    setProductsError(null);
    api
      .get<Product[]>("/products")
      .then((response) => {
        setProducts(response.data);
        if (response.data.length > 0) {
          setSelectedProductId((current) => current ?? response.data[0].id);
        }
      })
      .catch((err) => setProductsError(apiError(err)))
      .finally(() => setProductsLoading(false));
  }, [mode, products.length, productsLoading]);

  const runKnowledgeQuery = async (trimmed: string) => {
    const response = await queryInventoryAssistant(trimmed);
    setAnswer(response.answer);
    setSources(response.sources);
    setAgentResult(null);
    setMcpResult(null);
  };

  const runAgentQuery = async (trimmed: string) => {
    const response = await queryInventoryAgent(trimmed);
    setAnswer(response.answer);
    setAgentResult(response);
    setSources([]);
    setMcpResult(null);
  };

  const runMcpQuery = async (trimmed: string) => {
    const response = await queryMCPChat(trimmed, sessionId);
    setAnswer(response.output);
    setMcpResult(response);
    setSources([]);
    setAgentResult(null);
  };

  const runMultiAgentQuery = async (productIdValue: number) => {
    const response = await runMultiAgentAnalysis(productIdValue);
    setMultiAgentResult(response);
    setAnswer("");
    setSources([]);
    setAgentResult(null);
    setMcpResult(null);
  };

  const runQuery = async (value: string) => {
    if (mode === "multi-agent") {
      if (!selectedProductId) {
        setError("Select a product to analyze.");
        return;
      }
      setLoading(true);
      setError(null);
      try {
        await runMultiAgentQuery(selectedProductId);
      } catch (err) {
        setError(apiError(err));
      } finally {
        setLoading(false);
      }
      return;
    }

    const trimmed = value.trim();
    if (!trimmed) {
      setError("Enter a question about the inventory manual.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      if (mode === "agent") {
        await runAgentQuery(trimmed);
      } else if (mode === "mcp") {
        await runMcpQuery(trimmed);
      } else {
        await runKnowledgeQuery(trimmed);
      }
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void runQuery(question);
  };

  return (
    <div className="space-y-6">
      <section className="card overflow-hidden border-indigo-400/20 bg-gradient-to-br from-indigo-500/15 via-slate-900/40 to-cyan-400/[.06] p-0 shadow-xl">
        <div className="grid gap-0 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="p-6 sm:p-8">
            <span className="badge bg-cyan-400/10 text-cyan-300">{modeBadgeLabel(mode)}</span>
            <h1 className="mt-4 font-heading text-3xl font-extrabold text-white sm:text-4xl">Inventory Assistant</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-700 sm:text-base">
              Ask about inventory policies, stock levels, alerts, suppliers, dashboards, and procurement procedures.
            </p>

            <div className="mt-6 flex flex-wrap gap-2">
              {suggestedQuestions.map((item) => (
                <button
                  key={item}
                  className="rounded-full border border-white/10 bg-white/[.05] px-3 py-2 text-xs font-semibold text-slate-300 transition hover:border-cyan-300/50 hover:bg-cyan-400/10 hover:text-white"
                  type="button"
                  onClick={() => setQuestion(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-slate-200/80 bg-slate-950 px-6 py-6 text-slate-100 lg:border-l lg:border-t-0 sm:px-8">
            <ModeRulesList mode={mode} />
          </div>
        </div>
      </section>

      <section className="card">
        <form className="space-y-4" onSubmit={onSubmit}>
          <fieldset className="flex flex-wrap gap-2">
            <legend className="sr-only">Assistant mode</legend>
            <button className={mode === "knowledge" ? "btn-primary" : "btn-muted"} type="button" onClick={() => setMode("knowledge")}>
              Knowledge Mode
            </button>
            <button className={mode === "agent" ? "btn-primary" : "btn-muted"} type="button" onClick={() => setMode("agent")}>
              Agent Mode
            </button>
            <button className={mode === "mcp" ? "btn-primary" : "btn-muted"} type="button" onClick={() => setMode("mcp")}>
              MCP Chat Mode
            </button>
            <button className={mode === "multi-agent" ? "btn-primary" : "btn-muted"} type="button" onClick={() => setMode("multi-agent")}>
              Multi-Agent Analysis Mode
            </button>
          </fieldset>
          {mode === "multi-agent" ? (
            <ProductSelector
              products={products}
              loading={productsLoading}
              error={productsError}
              selectedProductId={selectedProductId}
              onSelect={setSelectedProductId}
              search={productSearch}
              onSearchChange={setProductSearch}
              categoryFilter={productCategoryFilter}
              onCategoryChange={setProductCategoryFilter}
            />
          ) : (
            <>
              <label className="block text-sm font-semibold text-slate-300" htmlFor="rag-question">
                Ask a question
              </label>
              <textarea
                id="rag-question"
                className="input min-h-[120px] resize-y"
                placeholder="What is reorder point?"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
              />
            </>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <button className="btn-primary min-w-[120px]" type="submit" disabled={loading}>
              {submitButtonLabel(loading, mode)}
            </button>
            <button
              className="btn-muted"
              type="button"
              onClick={() => {
                setQuestion("");
                setAnswer("");
                setSources([]);
                setAgentResult(null);
                setMultiAgentResult(null);
                setError(null);
              }}
            >
              Clear
            </button>
          </div>
        </form>

        {error ? <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
      </section>

      {mode === "multi-agent" ? (
        <MultiAgentDashboard result={multiAgentResult} />
      ) : (
      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <AnswerPanel loading={loading} answer={answer} agentResult={agentResult} mcpResult={mcpResult} />

        {mode === "mcp" ? <McpChatPanel mcpResult={mcpResult} conversationRef={conversationRef} /> : null}

        <section className="card">
          <h2 className="font-heading text-xl font-semibold">Sources</h2>
          {sources.length > 0 ? (
            <div className="mt-4 space-y-3">
              {sources.map((source, index) => (
                <article key={`${source.source}-${source.chunk_index ?? index}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{sourceLabel(source)}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{source.content}</p>
                </article>
              ))}
            </div>
          ) : (
            <p className="mt-3 text-sm leading-6 text-slate-500">Retrieved chunks will appear here after a question is answered.</p>
          )}
        </section>
      </div>
      )}
    </div>
  );
}
