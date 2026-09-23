import { qs, request } from "./http";

export interface Category {
  id: number;
  name: string;
  type: string;
}

export interface CreateCategoryBody {
  name: string;
  type: string;
}

export interface PatchCategoryBody {
  name: string;
}

export const categoriesApi = {
  list: (type: string | undefined, access: string) =>
    request<Category[]>(`/categories${qs({ type })}`, {}, access),
  create: (body: CreateCategoryBody, access: string) =>
    request<Category>("/categories", { method: "POST", body: JSON.stringify(body) }, access),
  patch: (id: number, body: PatchCategoryBody, access: string) =>
    request<Category>(`/categories/${id}`, { method: "PATCH", body: JSON.stringify(body) }, access),
  remove: (id: number, access: string) =>
    request<void>(`/categories/${id}`, { method: "DELETE" }, access),
};
