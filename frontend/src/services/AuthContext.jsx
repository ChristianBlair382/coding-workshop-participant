import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { apiClient, AUTH_CHANGED_EVENT } from "../api/client.js";

const AuthContext = createContext(null);

function decodeToken(token) {
    const payloadSegment = token.split('.')[1];
    return JSON.parse(atob(payloadSegment))
}

export function AuthProvider({children}) {
    const [token, setToken] = useState(() => localStorage.getItem('agricoreToken'));

    useEffect(() => {
        const syncToken = () => setToken(localStorage.getItem('agricoreToken'));
        window.addEventListener(AUTH_CHANGED_EVENT, syncToken);
        return () => window.removeEventListener(AUTH_CHANGED_EVENT, syncToken);
    }, []);

    const user = useMemo(() => (token ? decodeToken(token): null), [token]);

    const login = async (username, password) => {
        const LoginFormData = new URLSearchParams();
        LoginFormData.append('username', username);
        LoginFormData.append('password', password);

        const response = await apiClient.post('/auth/token', LoginFormData, {
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        });
        localStorage.setItem('agricoreToken', response.data.access_token);
        localStorage.setItem('agricoreRefreshToken', response.data.refresh_token);
        setToken(response.data.access_token);
    }

    const logout = () => {
        localStorage.removeItem('agricoreToken');
        localStorage.removeItem('agricoreRefreshToken');
        setToken(null);
    }

    const value = {token, user, isAuthenticated: Boolean(token), login, logout};

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
    const context = useContext(AuthContext);

    if (context === null) {
        throw new Error('useAuth must be used within AuthProvider')
    }
    return context;
}