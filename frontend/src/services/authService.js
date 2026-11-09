/**
 * Serviço de Autenticação e Sessão de Usuário.
 * Contrato oficial: Seção 7.1 do ARCHITECTURE.md.
 */
import { api } from './api';

const TOKEN_KEY = 'juripredict_token';
const USER_KEY = 'juripredict_user';

export const MOCK_USER = {
  id: 'usr-01',
  nome: 'Lucas Gabriel',
  oab: '12345/AL',
  email: 'advogado@escritorio.com',
};

/**
 * Realiza o login do profissional do direito.
 * Rota: POST /api/v1/auth/login
 */
export async function login(email, senha) {
  try {
    const data = await api.post('/auth/login', { email, senha });
    if (data.access_token) {
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(data.usuario));
    }
    return data;
  } catch (error) {
    console.info('[AuthService] Simulando login com usuário mock.');
    localStorage.setItem(TOKEN_KEY, 'mock-jwt-token-123456');
    localStorage.setItem(USER_KEY, JSON.stringify(MOCK_USER));
    return {
      access_token: 'mock-jwt-token-123456',
      token_type: 'bearer',
      usuario: MOCK_USER,
    };
  }
}

/**
 * Obtém os dados do advogado atualmente autenticado.
 */
export function getCurrentUser() {
  const user = localStorage.getItem(USER_KEY);
  return user ? JSON.parse(user) : MOCK_USER;
}

/**
 * Encerra a sessão do usuário.
 */
export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}
