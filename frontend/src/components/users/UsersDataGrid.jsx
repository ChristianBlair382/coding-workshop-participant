import { useCallback, useEffect, useMemo, useState } from "react";
import { DataGrid } from "@mui/x-data-grid";
import {
    Alert,
    Box,
    CircularProgress,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    MenuItem,
    Stack,
    TextField
} from "@mui/material";
import apiClient from "../../api/client.js";
import { useAuth } from "../../context/AuthContext.jsx";

const EMPTY_FORM_VALUES = {
    username: '',
    email: '',
    password: '',
    role: 'Employee',
};

const ROLE_VALUES = ['Facility_Admin', 'Engineer', 'Employee'];

export default function UsersDataGrid({onSuccess}) {
    const {user} = useAuth();
    const isAdmin = user?.role === 'Facility_Admin' || user?.role === 'FA';
    const [users, setUsers] = useState([]);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [manageDialogOpen, setManageDialogOpen] = useState(false);
    const [selectedUser, setSelectedUser] = useState(null);
    const [deleteConfirmation, setDeleteConfirmation] = useState(false);
    const [actionError, setActionError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form_values, setFormValues] = useState({...EMPTY_FORM_VALUES});

    async function fetchUsers() {
        setLoading(true);
        try {
            const response = await apiClient.get('/users');
            setUsers(response.data);
            setError(null);
        } catch {
            setError('Error: Could not load user data.');
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchUsers();
    }, []);

    const handleFieldChange = (field) => (event) => {
        setFormValues((prev) => ({...prev, [field]: event.target.value}));
    };

    const openManageDialog = useCallback((userRow) => {
        setSelectedUser(userRow);
        setFormValues({
            username: userRow.username,
            email: userRow.email,
            password: '',
            role: userRow.role,
        });
        setDeleteConfirmation(false);
        setActionError(null);
        setManageDialogOpen(true);
    }, []);

    const columns = useMemo(() => [
        {field: 'id', headerName: "ID", width: 70},
        {field: 'username', headerName: "Username", width: 140},
        {field: 'email', headerName: "Email", Width: 210},
        {field: 'role', headerName: "Role", width: 210},
        ...(isAdmin ? [{
            field: 'actions',
            headerName: 'Actions',
            width: 120,
            sortable: false,
            filterable: false,
            renderCell: ({row}) => (
                <Button size="small" onClick={() => openManageDialog(row)}>
                    Manage
                </Button>
            ),
        }] : []),
    ], [isAdmin, openManageDialog]);

    const handleCreate = async() => {
        {/* Check that there is an email provided and that it is valid. */}
        if (form_values.email.length <= 0) {
            setActionError('Must provide an email.');
            return;
        }
        {/* Check that the provided password is at minimum length. */}
        if (form_values.password.length < 8) {
            setActionError('Password must be at least 8 characters long.');
            return;
        }

        setActionError(null);
        try {
            await apiClient.post('/users', {
                ...form_values,
            });

            setDialogOpen(false);
            setFormValues({...EMPTY_FORM_VALUES});
            onSuccess(`User "${form_values.username}" created successfully.`);
            await fetchUsers();
        } catch {
            setActionError('Could not create user. Check the values and try again.');
        }
    };

    const handleUpdate = async() => {
        if (!selectedUser) return;

        if (form_values.email.length <= 0) {
            setActionError('Email must be provided.');
            return;
        }
        if (form_values.password.length < 8) {
            setActionError('Password must be at least 8 characters long.');
            return;
        }

        setSaving(true);
        setActionError(null);
        try {
            const response = await apiClient.patch(`/users/${selectedUser.id}`, {
                username: form_values.username,
                email: form_values.email,
                password: form_values.password,
                role: form_values.role,
            });
            setUsers((currentUsers) => currentUsers.map((userRow) => (
                userRow.id === selectedUser.id ? response.data : userRow
            )));
            setManageDialogOpen(false);
            onSuccess(`User ${response.data.username} updated successfully.`);
        } catch {
            setActionError('Could not update user. Check the values and try again.');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async() => {
        if (!selectedUser || !user?.sub || user.sub === selectedUser.username) return;

        setSaving(true);
        setActionError(null);
        try {
            await apiClient.delete(`/users/${selectedUser.id}`);
            setUsers((currentUsers) => currentUsers.filter((userRow) => userRow.id !== selectedUser.id));
            setManageDialogOpen(false);
            onSuccess(`User ${selectedUser.username} deleted successfully.`);
        } catch {
            setActionError('Could not delete user. It may still be in use.');
        } finally {
            setSaving(false);
        }
    };

    const openCreateDialog = () => {
        setFormValues({...EMPTY_FORM_VALUES});
        setActionError(null);
        setDialogOpen(true);
    };

    const canDeleteSelectedUser = Boolean(
        user?.sub && selectedUser && user.sub !== selectedUser.username
    );

    if (loading) return <CircularProgress/>;

    if (error) return <Alert severity="error">{error}</Alert>;

    return (
        <Box>
            <Box>
                <DataGrid
                    rows={users} 
                    columns={columns} 
                    getRowId={(row) => row.id}
                    initialState={{
                        pagination: {
                            paginationModel: {
                                pageSize: 5,
                            },
                        },
                    }}
                />
            </Box>
            {isAdmin && (
                <Button
                    variant="outlined"
                    sx={{mb: 2}}
                    onClick={openCreateDialog}
                >
                    Add User
                </Button>
            )}
            <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
                <DialogTitle>Create New User</DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{mt: 1, minWidth: 300}}>
                        {actionError && <Alert severity="error">{actionError}</Alert>}
                        <TextField label="Username" value={form_values.username} onChange={handleFieldChange('username')}/>
                        <TextField label="Email" value={form_values.email} onChange={handleFieldChange('email')}/>
                        <TextField type="password" label="Password" value={form_values.password} onChange={handleFieldChange('password')}/>
                        <TextField select label="Role" value={form_values.role} onChange={handleFieldChange('role')}>
                            {ROLE_VALUES.map((option) => (
                                <MenuItem key={option} value={option}>{option}</MenuItem>
                            ))}
                        </TextField>
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
                    <Button variant="contained" onClick={handleCreate}>Create</Button>
                </DialogActions>
            </Dialog>
            <Dialog
                open={manageDialogOpen}
                onClose={() => !saving && setManageDialogOpen(false)}
            >
                <DialogTitle>
                    {deleteConfirmation ? 'Delete User?' : `Manage User ${selectedUser?.id ?? ''}`}
                </DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{mt: 1, minWidth: 300}}>
                        {actionError && <Alert severity="error">{actionError}</Alert>}
                        {deleteConfirmation ? (
                            <Alert severity="warning">
                                Delete {selectedUser?.username}? This action cannot be undone.
                            </Alert>
                        ) : (
                            <>
                                <TextField label="Username" value={form_values.username} onChange={handleFieldChange('username')}/>
                                <TextField label="Email" value={form_values.email} onChange={handleFieldChange('email')}/>
                                <TextField type="password" label="Password" value={form_values.password} onChange={handleFieldChange('password')}/>
                                <TextField select label="Role" value={form_values.role} onChange={handleFieldChange('role')}>
                                    {ROLE_VALUES.map((option) => (
                                        <MenuItem key={option} value={option}>{option}</MenuItem>
                                    ))}
                                </TextField>
                            </>
                        )}
                    </Stack>
                </DialogContent>
                <DialogActions>
                    {deleteConfirmation ? (
                        <>
                            <Button onClick={() => setDeleteConfirmation(false)} disabled={saving}>Keep User</Button>
                            <Button color="error" variant="contained" onClick={handleDelete} disabled={saving}>
                                Delete User
                            </Button>
                        </>
                    ) : (
                        <>
                            <Button onClick={() => setManageDialogOpen(false)} disabled={saving}>Cancel</Button>
                            {canDeleteSelectedUser && (
                                <Button color="error" onClick={() => setDeleteConfirmation(true)} disabled={saving}>
                                    Delete
                                </Button>
                            )}
                            <Button variant="contained" onClick={handleUpdate} disabled={saving}>
                                Save Changes
                            </Button>
                        </>
                    )}
                </DialogActions>
            </Dialog>
        </Box>
    );
}