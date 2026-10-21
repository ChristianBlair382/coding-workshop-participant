import { useState } from "react";
import { Box, Paper, Alert, Button, Typography, TextField, CircularProgress } from "@mui/material";
import { useAuth } from "../../services/AuthContext.jsx";

export default function LoginForm() {
    const {login} = useAuth();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (event) => {
        event.preventDefault()
        setError(null);
        setLoading(true);
        try {
            await login(username, password);
        } catch (err) {
            if(err.response?.status === 401) {
                setError('Username or Password is incorrect.');
            } else {
                setError('Something went wrong! Please try again later.');
            }
        } finally {
            setLoading(false);
        }
    }

    return (
        <Box sx={{display: 'flex', justifyContent: 'center', mt: 8}}>
            <Paper
                component="form"
                onSubmit={handleSubmit}
                variant="outlined"
                sx={{p: 4, width: 320}}
            >   
                { error &&
                    <Alert severity="error" sx={{ mb: 2 }}>
                        {error}
                    </Alert>
                }
                <TextField 
                    label="Username"
                    fullWidth
                    margin="normal"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                />
                <TextField 
                    label="Password"
                    type="password"
                    fullWidth
                    margin="normal"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                />
                <Button
                    type="submit"
                    variant="contained"
                    fullWidth
                    disabled={loading}
                    sx={{ mb: 2, bgcolor: 'background.primary'}}
                >
                    {loading ? <CircularProgress size={24} color="inherit" /> : "Sign In"}
                </Button>
            </Paper>
        </Box>
    )
}