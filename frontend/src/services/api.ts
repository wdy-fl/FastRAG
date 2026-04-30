import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "",
  timeout: 60_000,
});

// 请求拦截器：预留 token 注入位置（当前无认证，为空实现）
api.interceptors.request.use((config) => {
  // const token = localStorage.getItem("token");
  // if (token) config.headers.Authorization = token;
  return config;
});

// 无响应拦截器 — FastRAG 直接返回数据，不需要解包
export default api;
