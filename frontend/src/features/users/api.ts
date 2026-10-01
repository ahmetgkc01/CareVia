import { apiRequest } from "../../shared/api/client";

export type ManagedUser = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  groups: string[];
  is_active: boolean;
  last_login: string | null;
  date_joined: string;
};

export type ManagedUserInput = {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  groups: string[];
  is_active: boolean;
  password?: string;
};

type PaginatedUsers = {
  count: number;
  next: string | null;
  previous: string | null;
  results: ManagedUser[];
};

export const userApi = {
  list: (search: string, page: number) => {
    const params = new URLSearchParams({ page: String(page), ordering: "last_name,first_name" });
    if (search) params.set("search", search);
    return apiRequest<PaginatedUsers>(`/api/users/?${params}`);
  },
  create: (user: ManagedUserInput) =>
    apiRequest<ManagedUser>("/api/users/", { method: "POST", body: JSON.stringify(user) }),
  update: (id: number, user: Partial<ManagedUserInput>) =>
    apiRequest<ManagedUser>(`/api/users/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(user),
    }),
};

