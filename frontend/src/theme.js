import { createTheme } from "@mui/material/styles";

const createAppTheme = (mode) => createTheme({
    palette: {
        item: {
            main: '#f0f298',
        },
        mode,
        ...(mode === 'dark' && {
            background: {
                primary: '#4a6c32',
                secondary: '#7b7c20',
                default: '#171c22',
                paper: '#222a32',
            },
            text: {
                primary: '#f4f7fa',
                secondary: '#878c91',
            },
        }),
        ...(mode === 'light' && {
            background: {
                primary: '#93d664',
                secondary: '#f0f298',
                default: '#f7f8fa',
                paper: '#ffffff',
            },
        }),
    },
    shape: {
        borderRadius: 4
    }
});

export default createAppTheme;