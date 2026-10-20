import { 
    AppBar, 
    Toolbar, 
    Typography, 
    Box, 
    Button,
    IconButton
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu'
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';

export default function AppHeader({onDrawerClick, mode, onToggleColorMode}) {
    return (
        <AppBar position='static' sx={{bgcolor: 'background.primary', color: '', borderBottom: 1, borderColor: 'divider'}}>
            <Toolbar sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    {onDrawerClick && (
                        <IconButton
                            aria-label="Open navigation drawer"
                            onClick={onDrawerClick}
                        >
                            <MenuIcon sx={{mr: 2}} />
                        </IconButton>
                    )}
                    <Typography variant="h6" component="h2">
                        ACME Incident Report Centre
                    </Typography>
                </Box>
                <Box sx={{ 
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                }}>
                    <IconButton
                        aria-label={`Switch to ${mode === 'light' ? 'dark' : 'light'} mode`}
                        onClick={onToggleColorMode}
                        color="inherit"
                        sx={{ml: 'auto'}}
                    >
                        {mode === 'light' ? <DarkModeIcon /> : <LightModeIcon />}
                    </IconButton>
                    <Typography sx={{ fontSize: 12, lineHeight: 1 }}>(Ctrl+.)</Typography>
                </Box>
            </Toolbar>
        </AppBar>
    )
}