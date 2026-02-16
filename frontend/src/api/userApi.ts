import api from "./axiosClient";

export interface UserProfile {
  name: string;
  skills: string[];
  preferredLocations: string[];
  fields: string[];
}

export async function getProfile(): Promise<UserProfile> {
  const res = await api.get<UserProfile>("/user/profile");
  return res.data;
}

export async function updateProfile(data: UserProfile): Promise<UserProfile> {
  const res = await api.put<UserProfile>("/user/profile", data);
  return res.data;
}
