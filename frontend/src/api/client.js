import axios from 'axios'

export const apiClient = axios.create({
   baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
});

export const AUTH_CHANGED_EVENT = 'acme:auth-changed';

let refreshPromise = null;

function clearTokens() {
    localStorage.removeItem('acmeToken');
    localStorage.removeItem('acmeRefreshToken');
    window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem('acmeToken');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        const isAuthRequest = originalRequest?.url?.includes('/auth/token')
            || originalRequest?.url?.includes('/auth/refresh');

        if (
            error.response?.status !== 401
            || !originalRequest
            || originalRequest._retry
            || isAuthRequest
        ) {
            return Promise.reject(error);
        }

        const refreshToken = localStorage.getItem('acmeRefreshToken');
        if (!refreshToken) {
            clearTokens();
            return Promise.reject(error);
        }

        originalRequest._retry = true;

        try {
            if (!refreshPromise) {
                refreshPromise = axios
                    .post(apiClient.getUri({ url: '/auth/refresh' }), {
                        refresh_token: refreshToken,
                    })
                    .then((response) => {
                        localStorage.setItem('acmeToken', response.data.access_token);
                        localStorage.setItem('acmeRefreshToken', response.data.refresh_token);
                        window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
                        return response.data.access_token;
                    })
                    .finally(() => {
                        refreshPromise = null;
                    });
            }

            const accessToken = await refreshPromise;
            originalRequest.headers.Authorization = `Bearer ${accessToken}`;
            return apiClient(originalRequest);
        } catch (refreshError) {
            clearTokens();
            return Promise.reject(refreshError);
        }
    },
);

export default apiClient;