import api from "./axiosClient";

export interface CompanyInfo {
  size: string;
  founded: string;
  business: string;
}

export interface InternPost {
  id: string;
  title: string;
  company: string;
  base: string;
  date: string;
  description: string;
  requirements: string[];
  applyLink: string;
  companyInfo: CompanyInfo;
  fitScore: string;
  difficulty: string;
  avgSalary: string;
}

export async function getAllInterns(): Promise<InternPost[]> {
  const res = await api.get<InternPost[]>("/interns");
  return res.data;
}

export async function getInternById(id: string): Promise<InternPost> {
  const res = await api.get<InternPost>(`/interns/${id}`);
  return res.data;
}
