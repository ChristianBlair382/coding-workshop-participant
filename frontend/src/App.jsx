import { useCallback, useEffect, useMemo, useState } from "react";

/* MATERIAL UI COMPONENTS */
import {
  Container,
  Typography,
  Box,
  Button,
  Snackbar,
  Alert,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItem,
  ListItemIcon,
  ListItemButton,
  ListItemText,
  Drawer
} from "@mui/material";
import { CssBaseline, ThemeProvider, useMediaQuery } from "@mui/material";

/* EXTERNAL IMPORTS */
import { AuthProvider, useAuth } from "./services/AuthContext.jsx";
import createAppTheme from "./theme.js";
import apiClient from "./api/client.js";
import AppHeader from "./components/layout/AppHeader.jsx";
import LoginForm from "./components/auth/LoginForm.jsx";
import UsersDataGrid from "./components/users/UsersDataGrid.jsx";
import RolesAndPermissionsDataGrid from "./components/users/RolesAndPermissionsDataGrid.jsx";
import EngineersDataGrid from "./components/engineers/EngineersDataGrid.jsx";
import FacilitiesDataGrid from "./components/facilities/FacilitiesDataGrid.jsx";
import IncidentTicketsDataGrid from "./components/incident_tickets/IncidentTicketsDataGrid.jsx";
import DashboardSummaries from "./components/layout/DashboardSummaries.jsx";

/* ICON IMPORTS */
import GridViewIcon from '@mui/icons-material/GridView';
import WarehouseIcon from '@mui/icons-material/Warehouse';
import AssignmentIcon from '@mui/icons-material/Assignment';
import EngineeringIcon from '@mui/icons-material/Engineering';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';

function Dashboard({mode, onToggleColorMode}) {
  const {user, logout} = useAuth()
  const [notification, setNotification] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [permissionsDialogOpen, setPermissionsDialogOpen] = useState(false)
  const [rolePermissions, setRolePermissions] = useState(null)
  const [permissionsLoading, setPermissionsLoading] = useState(false)
  const [permissionsError, setPermissionsError] = useState('')
  const [selectedPage, setSelectedPage] = useState('summaries')
  const [completionRefreshKey, setCompletionRefreshKey] = useState(0)

  const isFA = user?.role === 'Facility_Admin' || user?.role === 'FA';
  const isEngineer = user?.role === 'Engineer' || user?.role === 'ENG';
  const toggleDrawer = (newOpen) => () => {
    setDrawerOpen(newOpen);
  };
  const displaySelectedPage = (string) => () => {
    setSelectedPage(string)
  }
  const openPermissionsDialog = () => {
    setPermissionsLoading(true);
    setPermissionsError('');
    setRolePermissions(null);
    setPermissionsDialogOpen(true);
  }

  /* DRAWER CONSTRUCT */
  const DrawerList = (
    <Box sx={{ width: 300, height: "100%", display: "flex", flexDirection: "column", }} role="presentation" onClick={toggleDrawer(false)}>
      <List>
        <ListItem>
          <ListItemButton color="inherit" onClick={displaySelectedPage('summaries')}>
            <ListItemIcon color="secondary">
              <GridViewIcon />
            </ListItemIcon>
            <ListItemText primary="Dashboard"/>
          </ListItemButton>
        </ListItem>
        {isFA && (
        <ListItem>
          <ListItemButton color="inherit" onClick={displaySelectedPage('facilities')}>
            <ListItemIcon color="secondary">
              <WarehouseIcon />
            </ListItemIcon>
            <ListItemText primary="Facilities"/>
          </ListItemButton>
        </ListItem>
        )}
        <ListItem>
          <ListItemButton color="inherit" onClick={displaySelectedPage('incident_tickets')}>
            <ListItemIcon color="secondary">
              <AssignmentIcon />
            </ListItemIcon>
            <ListItemText primary="Incident Tickets"/>
          </ListItemButton>
        </ListItem>
        {(isFA || isEngineer) && <ListItem>
          <ListItemButton color="inherit" onClick={displaySelectedPage('engineers')}>
            <ListItemIcon color="secondary">
              <EngineeringIcon />
            </ListItemIcon>
            <ListItemText primary="Engineers"/>
          </ListItemButton>
        </ListItem>}
        { isFA && (
          <>
            <ListItem>
              <ListItemButton color="inherit" onClick={displaySelectedPage('users')}>
                <ListItemIcon color="secondary">
                  <AccountCircleIcon />
                </ListItemIcon>
                <ListItemText primary="Users"/>
              </ListItemButton>
            </ListItem>
          </>
        )}
      </List>
      <Box 
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'stretch',
          mt: 'auto'
        }}
      >
        <ListItemButton
          onClick={openPermissionsDialog}
          aria-haspopup="dialog"
          aria-label={`View role and permissions for ${user?.sub}`}
        >
          <ListItemText
            primary={user?.sub}
            secondary={user?.role?.replace(/_/g, ' ')}
          />
        </ListItemButton>
        <Button sx={{bgcolor: 'background.secondary'}} color="inherit" onClick={logout}>Log Out</Button>
      </Box>
    </Box>
  );

  useEffect(() => {
    if (!permissionsDialogOpen) return undefined;

    let cancelled = false;

    apiClient.get('/users/me/permissions')
      .then((response) => {
        if (!cancelled) setRolePermissions(response.data);
      })
      .catch((error) => {
        if (!cancelled) {
          setPermissionsError(
            error.response?.data?.detail ?? 'Could not load your permissions.'
          );
        }
      })
      .finally(() => {
        if (!cancelled) setPermissionsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [permissionsDialogOpen]);

  const handleGridSuccess = (message) => {
    setNotification(message);
    setCompletionRefreshKey((currentKey) => currentKey + 1);
  };

  return (
    <>
      <AppHeader
        onDrawerClick={toggleDrawer(true)}
        mode={mode}
        onToggleColorMode={onToggleColorMode}
      />
      <Drawer open={drawerOpen} onClose={toggleDrawer(false)}>
        {DrawerList}
      </Drawer>
      <Dialog
        open={permissionsDialogOpen}
        onClose={() => setPermissionsDialogOpen(false)}
        fullWidth
        maxWidth="sm"
        aria-labelledby="role-permissions-dialog-title"
      >
        <DialogTitle id="role-permissions-dialog-title">
          {user.sub}
        </DialogTitle>
        <DialogContent dividers>
          <Typography variant="subtitle1" sx={{mb: 1}}>
            Role: {(rolePermissions?.role ?? user?.role)?.replace(/_/g, ' ')}
          </Typography>
          {permissionsLoading ? (
            <CircularProgress size={24} aria-label="Loading permissions" />
          ) : permissionsError ? (
            <Alert severity="error">{permissionsError}</Alert>
          ) : rolePermissions?.permissions?.length ? (
            <List disablePadding>
              {rolePermissions.permissions.map(({name, description}) => (
                <ListItem key={name} divider disableGutters>
                  <ListItemText
                    primary={name}
                    secondary={description}
                  />
                </ListItem>
              ))}
            </List>
          ) : (
            <Typography>No permissions are assigned to this role.</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPermissionsDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
      
      <Container sx={{ padding: 4 }}>
        {isFA && selectedPage === 'facilities' && (
          <>
            <Typography
              variant="h5"
              component="h2"
              gutterBottom
            >
              Facilities
            </Typography>
            <Box sx={{mb: 4}}>
              <FacilitiesDataGrid
                onSuccess={handleGridSuccess}
                refreshKey={completionRefreshKey}
              />
            </Box>
          </>
        )}
        {selectedPage === 'incident_tickets' && (
          <>
            <Typography
              variant="h5"
              component="h2"
              gutterBottom
            >
              Incident Tickets
            </Typography>
            <Box sx={{mb: 4}}>
              <IncidentTicketsDataGrid
                onSuccess={handleGridSuccess}
                refreshKey={completionRefreshKey}
              />
            </Box>
          </>
        )}
        {(isFA || isEngineer) && selectedPage === 'engineers' && (
          <>
            <Typography
              variant="h5"
              component="h2"
              gutterBottom
            >
              Engineers
            </Typography>
            <Box sx={{mb: 4}}>
              <EngineersDataGrid
                onSuccess={handleGridSuccess}
                refreshKey={completionRefreshKey}
              />
            </Box>
          </>
        )}
        { isFA && selectedPage === 'users' && 
          <>
            <Typography
            variant="h5"
            component="h2"
            gutterBottom
            >
              Users
            </Typography>
            <Box sx={{mb: 4}}>
              <UsersDataGrid onSuccess={handleGridSuccess} />
            </Box>
            <Typography variant="h5" component="h2" gutterBottom>
              Roles and Permissions
            </Typography>
            <Box sx={{mb: 4}}>
              <RolesAndPermissionsDataGrid />
            </Box>
          </>
        }
        {selectedPage === 'summaries' && (
          <DashboardSummaries refreshKey={completionRefreshKey} />
        )}
      </Container>
      
      <Snackbar 
        open={Boolean(notification)}
        autoHideDuration={4000}
        onClose={() => setNotification(null)}
      >
        <Alert severity="success" onClose={() => setNotification(null)}>{notification}</Alert>
      </Snackbar>
    </>
  );
}

function AppContent({mode, onToggleColorMode}) {
  const {isAuthenticated} = useAuth();
  return isAuthenticated
    ? <Dashboard mode={mode} onToggleColorMode={onToggleColorMode} />
    : (
      <>
        <AppHeader mode={mode} onToggleColorMode={onToggleColorMode} />
        <LoginForm />
      </>
    );
}

function App() {
  const [colorModePreference, setColorModePreference] = useState(() => {
    try {
      const savedPreference = localStorage.getItem("citibankColorMode");
      return savedPreference === "light" || savedPreference === "dark" ? savedPreference : "system";
    } catch (error) {
      console.warn("Could not read the saved color preference; Defaulting to system theme settings...", error);
      return "system";
    }
  });
  const prefersDarkMode = useMediaQuery("(prefers-color-scheme: dark)");
  const mode = colorModePreference === "system" ? (prefersDarkMode ? "dark" : "light") : colorModePreference;
  const theme = useMemo(() => createAppTheme(mode), [mode]);

  useEffect(() => {
    try {
      window.localStorage.setItem('citibankColorMode', colorModePreference)
    } catch (error) {
      console.warn("Could not save current color preference; will not remain persistent after this session. Sorry!", error);
    }
    document.documentElement.dataset.colorMode = mode;
  }, [colorModePreference, mode]);

  const toggleColorMode = useCallback(() => {
    setColorModePreference((currentPreference) => (
      currentPreference === "dark" ? "light" : "dark"
    ));
  }, []);

  useEffect(() => {
    function handleKeyShortcut(e){
      const isCtrlOrCmd = e.ctrlKey || e.metaKey
      if (isCtrlOrCmd && e.key === "."){
        e.preventDefault();
        toggleColorMode();
      }
    }
    window.addEventListener("keydown", handleKeyShortcut);
    return () => window.removeEventListener("keydown", handleKeyShortcut);
  }, [toggleColorMode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <AppContent mode={mode} onToggleColorMode={toggleColorMode} />
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App