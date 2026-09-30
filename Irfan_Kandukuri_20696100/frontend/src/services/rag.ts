import { api } from "./api";
import type { AgentQueryResponse, MCPChatResponse, MultiAgentAnalysisResponse, RagQueryResponse } from "../types";

export async function queryInventoryAssistant(question: string): Promise<RagQueryResponse> {
  const response = await api.post<RagQueryResponse>("/rag/query", { question });
  return response.data;
}

export async function queryInventoryAgent(question: string): Promise<AgentQueryResponse> {
  const response = await api.post<AgentQueryResponse>("/agent/query", { question });
  return response.data;
}

export async function queryMCPChat(message: string, sessionId: string): Promise<MCPChatResponse> {
  const response = await api.post<MCPChatResponse>("/mcp/chat", { message, session_id: sessionId });
  return response.data;
}

export async function getMCPHistory(sessionId: string): Promise<MCPChatResponse> {
  const response = await api.get<MCPChatResponse>(`/mcp/sessions/${encodeURIComponent(sessionId)}`);
  return response.data;
}

export async function runMultiAgentAnalysis(productId: number): Promise<MultiAgentAnalysisResponse> {
  const response = await api.post<MultiAgentAnalysisResponse>("/multi-agent/analyze", { product_id: productId });
  return response.data;
}
