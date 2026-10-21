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
    Stack,
    TextField,
    Typography,
} from "@mui/material";
import apiClient from "../../api/client.js";
import FacilityMap from "./FacilityMap.jsx";

const EMPTY_FORM = {name: "", location: "", floor_count: "0"};

/**
 * Lists facilities and opens the selected facility's map on demand.
 *
 * @param {{onSuccess: (message: string) => void, refreshKey: number}} props Component props.
 * @returns {JSX.Element} Facility grid or the selected facility map.
 */
export default function FacilitiesDataGrid({onSuccess, refreshKey}) {
    const [facilities, setFacilities] = useState([]);
    const [selectedFacility, setSelectedFacility] = useState(null);
    const [editingFacility, setEditingFacility] = useState(null);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [deleteConfirmation, setDeleteConfirmation] = useState(false);
    const [form, setForm] = useState({...EMPTY_FORM});
    const [actionError, setActionError] = useState("");
    const [saving, setSaving] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const fetchFacilities = useCallback(async () => {
        try {
            const response = await apiClient.get("/buildings");
            setFacilities(response.data);
            setError("");
        } catch (requestError) {
            setError(requestError.response?.data?.detail ?? "Could not load facilities.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        let cancelled = false;
        Promise.resolve().then(() => {
            if (!cancelled) fetchFacilities();
        });
        return () => {
            cancelled = true;
        };
    }, [fetchFacilities, refreshKey]);

    const openCreateDialog = () => {
        setEditingFacility(null);
        setForm({...EMPTY_FORM});
        setDeleteConfirmation(false);
        setActionError("");
        setDialogOpen(true);
    };

    const openEditDialog = useCallback((facility) => {
        setEditingFacility(facility);
        setForm({
            name: facility.name,
            location: facility.location,
            floor_count: "0",
        });
        setDeleteConfirmation(false);
        setActionError("");
        setDialogOpen(true);
    }, []);

    const handleSave = async () => {
        setSaving(true);
        setActionError("");
        const payload = {
            name: form.name.trim(),
            location: form.location.trim(),
        };
        try {
            if (editingFacility) {
                const response = await apiClient.patch(
                    `/buildings/${editingFacility.id}`,
                    payload,
                );
                setFacilities((current) => current.map((facility) => (
                    facility.id === editingFacility.id ? response.data : facility
                )));
                onSuccess(`Facility "${response.data.name}" updated.`);
            } else {
                const response = await apiClient.post("/buildings", {
                    ...payload,
                    floor_count: Number(form.floor_count),
                });
                setFacilities((current) => [...current, response.data]);
                onSuccess(`Facility "${response.data.name}" created.`);
            }
            setDialogOpen(false);
        } catch (requestError) {
            setActionError(
                requestError.response?.data?.detail ?? "Could not save the facility.",
            );
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!editingFacility) return;
        setSaving(true);
        setActionError("");
        try {
            await apiClient.delete(`/buildings/${editingFacility.id}`);
            setFacilities((current) => current.filter(
                (facility) => facility.id !== editingFacility.id,
            ));
            setDialogOpen(false);
            onSuccess(`Facility "${editingFacility.name}" deleted.`);
        } catch (requestError) {
            setActionError(
                requestError.response?.data?.detail ?? "Could not delete the facility.",
            );
        } finally {
            setSaving(false);
        }
    };

    const columns = useMemo(() => [
        {field: "id", headerName: "ID", width: 90},
        {field: "name", headerName: "Facility", minWidth: 200, flex: 1},
        {field: "location", headerName: "Location", minWidth: 220, flex: 1},
        {field: "floor_count", headerName: "Floors", width: 110},
        {
            field: "actions",
            headerName: "Actions",
            width: 190,
            sortable: false,
            filterable: false,
            renderCell: ({row}) => (
                <Stack direction="row" spacing={1}>
                    <Button size="small" onClick={() => setSelectedFacility(row)}>
                        View
                    </Button>
                    <Button size="small" onClick={() => openEditDialog(row)}>
                        Manage
                    </Button>
                </Stack>
            ),
        },
    ], [openEditDialog]);

    if (selectedFacility) {
        return (
            <Stack spacing={2}>
                <Box>
                    <Button onClick={() => setSelectedFacility(null)}>Back to Facilities</Button>
                    <Typography variant="h6" component="h3" sx={{mt: 1}}>
                        {selectedFacility.name}
                    </Typography>
                </Box>
                <FacilityMap
                    buildingId={selectedFacility.id}
                    onSuccess={onSuccess}
                    refreshKey={refreshKey}
                />
            </Stack>
        );
    }

    if (loading) return <CircularProgress aria-label="Loading facilities" />;
    if (error) return <Alert severity="error">{error}</Alert>;

    return (
        <Box sx={{width: "100%"}}>
            <Button variant="outlined" sx={{mb: 2}} onClick={openCreateDialog}>
                Add Facility
            </Button>
            {facilities.length === 0 ? (
                <Alert severity="info">No facilities have been added yet.</Alert>
            ) : (
                <DataGrid
                    aria-label="Facilities"
                    rows={facilities}
                    columns={columns}
                    autoHeight
                    disableRowSelectionOnClick
                    pageSizeOptions={[5, 10, 25]}
                    initialState={{pagination: {paginationModel: {pageSize: 10}}}}
                />
            )}
            <Dialog
                open={dialogOpen}
                onClose={() => !saving && setDialogOpen(false)}
                fullWidth
                maxWidth="sm"
            >
                <DialogTitle>
                    {deleteConfirmation
                        ? "Delete Facility?"
                        : editingFacility
                            ? `Manage Facility ${editingFacility.id}`
                            : "Add Facility"}
                </DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{mt: 1}}>
                        {actionError && <Alert severity="error">{actionError}</Alert>}
                        {deleteConfirmation ? (
                            <Alert severity="warning">
                                Delete "{editingFacility?.name}"? This action cannot be undone.
                                Its floors and seats will also be deleted.
                            </Alert>
                        ) : (
                            <>
                                <TextField
                                    required
                                    label="Facility name"
                                    value={form.name}
                                    onChange={(event) => setForm({
                                        ...form,
                                        name: event.target.value,
                                    })}
                                    inputProps={{maxLength: 100}}
                                />
                                <TextField
                                    required
                                    label="Location"
                                    value={form.location}
                                    onChange={(event) => setForm({
                                        ...form,
                                        location: event.target.value,
                                    })}
                                    inputProps={{maxLength: 50}}
                                />
                                {!editingFacility && (
                                    <TextField
                                        required
                                        type="number"
                                        label="Initial floors"
                                        value={form.floor_count}
                                        onChange={(event) => setForm({
                                            ...form,
                                            floor_count: event.target.value,
                                        })}
                                        inputProps={{min: 0, step: 1}}
                                        helperText="Creates this many floor records when the facility is created."
                                    />
                                )}
                            </>
                        )}
                    </Stack>
                </DialogContent>
                <DialogActions>
                    {deleteConfirmation ? (
                        <>
                            <Button onClick={() => setDeleteConfirmation(false)} disabled={saving}>
                                Cancel
                            </Button>
                            <Button
                                color="error"
                                variant="contained"
                                onClick={handleDelete}
                                disabled={saving}
                            >
                                Delete Facility
                            </Button>
                        </>
                    ) : (
                        <>
                            <Button onClick={() => setDialogOpen(false)} disabled={saving}>
                                Cancel
                            </Button>
                            {editingFacility && (
                                <Button
                                    color="error"
                                    onClick={() => {
                                        setActionError("");
                                        setDeleteConfirmation(true);
                                    }}
                                    disabled={saving}
                                >
                                    Delete
                                </Button>
                            )}
                            <Button
                                variant="contained"
                                onClick={handleSave}
                                disabled={
                                    saving
                                    || !form.name.trim()
                                    || !form.location.trim()
                                    || (!editingFacility && (
                                        !Number.isInteger(Number(form.floor_count))
                                        || Number(form.floor_count) < 0
                                    ))
                                }
                            >
                                {editingFacility ? "Save Changes" : "Create Facility"}
                            </Button>
                        </>
                    )}
                </DialogActions>
            </Dialog>
        </Box>
    );
}

FacilitiesDataGrid.propTypes = {
    onSuccess: PropTypes.func,
    refreshKey: PropTypes.number,
};

FacilitiesDataGrid.defaultProps = {
    onSuccess: () => {},
    refreshKey: 0,
};