/**
 * Cliente HTTP Base para comunicação com o Backend FastAPI.
 * Conforme especificado na Seção 7 do ARCHITECTURE.md.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

/**
 * Recupera o token JWT do localStorage se o usuário estiver autenticado.
 */
function getAuthHeader() {
  const token = localStorage.getItem('juripredict_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Wrapper de requisições HTTP utilizando fetch nativo.
 */
export async function apiRequest(endpoint, { method = 'GET', body = null, isFormData = false, headers = {} } = {}) {
  const url = `${API_BASE_URL}${endpoint}`;

  const defaultHeaders = {
    ...getAuthHeader(),
    ...headers,
  };

  if (!isFormData) {
    defaultHeaders['Content-Type'] = 'application/json';
  }

  const config = {
    method,
    headers: defaultHeaders,
  };

  if (body) {
    config.body = isFormData ? body : JSON.stringify(body);
  }

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const error = new Error(errorData.detail || `Erro HTTP ${response.status}: ${response.statusText}`);
      error.status = response.status;
      error.data = errorData;
      throw error;
    }

    // Se a resposta for um stream de arquivo (PDF)
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/pdf')) {
      return await response.blob();
    }

    return await response.json();
  } catch (error) {
    // Se a conexão for recusada ou offline, repassa com indicação
    if (error.message.includes('Failed to fetch') || error.name === 'TypeError') {
      console.warn(`[JuriPredict API] Backend indisponível em ${url}. Ativando mock fallback.`);
      error.isNetworkError = true;
    }
    throw error;
  }
}

export const api = {
  get: (endpoint, options = {}) => apiRequest(endpoint, { ...options, method: 'GET' }),
  post: (endpoint, body, options = {}) => apiRequest(endpoint, { ...options, method: 'POST', body }),
  put: (endpoint, body, options = {}) => apiRequest(endpoint, { ...options, method: 'PUT', body }),
  delete: (endpoint, options = {}) => apiRequest(endpoint, { ...options, method: 'DELETE' }),
};

export default api;
