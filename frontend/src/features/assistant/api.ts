import { apiRequest } from "../../shared/api/client";

export type AssistantSource = {
  label: string;
  updated_at: string | null;
};

export type AssistantMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  category: string;
  safety_code: string;
  sources: AssistantSource[];
  created_at: string;
};

export type AssistantInput = {
  message: string;
  language: "tr" | "en";
  patient_id?: string;
};

export const assistantApi = {
  history: () => apiRequest<AssistantMessage[]>("/api/assistant/messages/"),
  send: (input: AssistantInput) =>
    apiRequest<AssistantMessage>("/api/assistant/messages/", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  clear: () => apiRequest<void>("/api/assistant/messages/", { method: "DELETE" }),
};
