import api from "./axiosClient";

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  token: string | null;
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>("/auth/login", data);
  return res.data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}
