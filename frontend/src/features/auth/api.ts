import { apiRequest } from "../../shared/api/client";

export type CurrentUser = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  groups: string[];
};

export const authApi = {
  csrf: () => apiRequest<{ detail: string }>("/api/session/csrf/"),
  me: () => apiRequest<CurrentUser>("/api/session/me/"),
  login: (credentials: { username: string; password: string }) =>
    apiRequest<CurrentUser>("/api/session/login/", {
      method: "POST",
      body: JSON.stringify(credentials),
    }),
  logout: () => apiRequest<void>("/api/session/logout/", { method: "POST" }),
};

