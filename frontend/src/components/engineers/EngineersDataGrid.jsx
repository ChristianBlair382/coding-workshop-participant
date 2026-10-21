import { useCallback, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { DataGrid } from "@mui/x-data-grid";
import {
    Alert,
    Box,
    Button,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    MenuItem,
    Stack,
    TextField,
} from "@mui/material";
import apiClient from "../../api/client.js";
import { useAuth } from "../../services/AuthContext.jsx";

const FIELD_OPTIONS = ["Building", "Hardware", "Software", "Electrical"];
const STATUS_OPTIONS = ["Available", "Unavailable"];
const EMPTY_FORM = {name: "", user_id: "", field: "Building", status: "Available"};

/**
 * Displays engineer profiles and provides admin-only profile management.
 *
 * @param {{onSuccess: (message: string) => void, refreshKey: number}} props Component props.
 * @returns {JSX.Element} Engineer profile grid.
 */
export default function EngineersDataGrid({onSuccess, refreshKey}) {
    const {user} = useAuth();
    const isAdmin = ["Facility_Admin", "FA"].includes(user?.role);
    const [engineers, setEngineers] = useState([]);
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [dialogOpen, setDialogOpen] = useState(false);
    const [selectedEngineer, setSelectedEngineer] = useState(null);
    const [form, setForm] = useState({...EMPTY_FORM});
    const [actionError, setActionError] = useState("");
    const [saving, setSaving] = useState(false);

    const fetchData = useCallback(async () => {
        try {
            const requests = [apiClient.get("/engineers")];
            if (isAdmin) requests.push(apiClient.get("/users"));
            const [engineerResponse, userResponse] = await Promise.all(requests);
            setEngineers(engineerResponse.data);
            if (userResponse) setUsers(userResponse.data);
            setError("");
        } catch (requestError) {
            setError(requestError.response?.data?.detail ?? "Could not load engineer profiles.");
        } finally {
            setLoading(false);
        }
    }, [isAdmin]);

    useEffect(() => {
        let cancelled = false;
        Promise.resolve().then(() => {
            if (!cancelled) fetchData();
        });
        return () => {
            cancelled = true;
        };
    }, [fetchData, refreshKey]);

    const openCreateDialog = () => {
        setSelectedEngineer(null);
        setForm({...EMPTY_FORM});
        setActionError("");
        setDialogOpen(true);
    };

    const openEditDialog = useCallback((engineer) => {
        setSelectedEngineer(engineer);
        setForm({
            name: engineer.name,
            user_id: String(engineer.user_id),
            field: engineer.field,
            status: engineer.status,
        });
        setActionError("");
        setDialogOpen(true);
    }, []);

    const handleSave = async () => {
        setSaving(true);
        setActionError("");
        try {
            if (selectedEngineer) {
                const response = await apiClient.patch(`/engineers/${selectedEngineer.id}`, {
                    name: form.name,
                    field: form.field,
                    status: form.status,
                });
                setEngineers((current) => current.map((engineer) => (
                    engineer.id === selectedEngineer.id ? response.data : engineer
                )));
                onSuccess(`Engineer "${response.data.name}" updated.`);
            } else {
                await apiClient.post("/engineers", {
                    ...form,
                    user_id: Number(form.user_id),
                });
                onSuccess(`Engineer "${form.name}" created.`);
                await fetchData();
            }
            setDialogOpen(false);
        } catch (requestError) {
            setActionError(requestError.response?.data?.detail ?? "Could not save the engineer profile.");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!selectedEngineer) return;
        setSaving(true);
        setActionError("");
        try {
            await apiClient.delete(`/engineers/${selectedEngineer.id}`);
            setEngineers((current) => current.filter((engineer) => engineer.id !== selectedEngineer.id));
            setDialogOpen(false);
            onSuccess(`Engineer "${selectedEngineer.name}" deleted.`);
        } catch (requestError) {
            setActionError(requestError.response?.data?.detail ?? "Could not delete the engineer profile.");
        } finally {
            setSaving(false);
        }
    };

    const columns = useMemo(() => [
        {field: "id", headerName: "ID", width: 80},
        {field: "name", headerName: "Name", minWidth: 180, flex: 1},
        {field: "user_id", headerName: "User ID", width: 110},
        {field: "field", headerName: "Specialty", minWidth: 150, flex: 0.8},
        {field: "status", headerName: "Status", minWidth: 140, flex: 0.7},
        ...(isAdmin ? [{
            field: "actions",
            headerName: "Actions",
            width: 120,
            sortable: false,
            filterable: false,
            renderCell: ({row}) => (
                <Button size="small" onClick={() => openEditDialog(row)}>Manage</Button>
            ),
        }] : []),
    ], [isAdmin, openEditDialog]);

    if (loading) return <CircularProgress aria-label="Loading engineers" />;
    if (error) return <Alert severity="error">{error}</Alert>;

    return (
        <Box sx={{width: "100%"}}>
            {isAdmin && (
                <Button variant="outlined" sx={{mb: 2}} onClick={openCreateDialog}>
                    Add Engineer
                </Button>
            )}
            <DataGrid
                rows={engineers}
                columns={columns}
                autoHeight
                disableRowSelectionOnClick
                pageSizeOptions={[5, 10, 25]}
                initialState={{pagination: {paginationModel: {pageSize: 10}}}}
            />
            <Dialog open={dialogOpen} onClose={() => !saving && setDialogOpen(false)} fullWidth>
                <DialogTitle>{selectedEngineer ? "Manage Engineer" : "Add Engineer"}</DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{mt: 1}}>
                        {actionError && <Alert severity="error">{actionError}</Alert>}
                        {!selectedEngineer && (
                            <TextField
                                select
                                required
                                label="User account"
                                value={form.user_id}
                                onChange={(event) => setForm({...form, user_id: event.target.value})}
                            >
                                {users.filter((account) => ["Engineer", "ENG"].includes(account.role)).map((account) => (
                                    <MenuItem key={account.id} value={account.id}>
                                        {account.username} ({account.role})
                                    </MenuItem>
                                ))}
                            </TextField>
                        )}
                        <TextField
                            required
                            label="Name"
                            value={form.name}
                            onChange={(event) => setForm({...form, name: event.target.value})}
                        />
                        <TextField
                            select
                            label="Specialty"
                            value={form.field}
                            onChange={(event) => setForm({...form, field: event.target.value})}
                        >
                            {FIELD_OPTIONS.map((field) => <MenuItem key={field} value={field}>{field}</MenuItem>)}
                        </TextField>
                        <TextField
                            select
                            label="Status"
                            value={form.status}
                            onChange={(event) => setForm({...form, status: event.target.value})}
                        >
                            {STATUS_OPTIONS.map((status) => <MenuItem key={status} value={status}>{status}</MenuItem>)}
                        </TextField>
                    </Stack>
                </DialogContent>
                <DialogActions>
                    {selectedEngineer && (
                        <Button color="error" onClick={handleDelete} disabled={saving}>Delete</Button>
                    )}
                    <Button onClick={() => setDialogOpen(false)} disabled={saving}>Cancel</Button>
                    <Button
                        variant="contained"
                        onClick={handleSave}
                        disabled={saving || !form.name.trim() || (!selectedEngineer && !form.user_id)}
                    >
                        Save
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}

EngineersDataGrid.propTypes = {
    onSuccess: PropTypes.func,
    refreshKey: PropTypes.number,
};

EngineersDataGrid.defaultProps = {
    onSuccess: () => {},
    refreshKey: 0,
};