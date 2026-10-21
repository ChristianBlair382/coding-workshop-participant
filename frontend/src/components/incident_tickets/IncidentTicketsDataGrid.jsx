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
    Typography,
} from "@mui/material";
import apiClient from "../../api/client.js";
import { useAuth } from "../../services/AuthContext.jsx";
import IncidentTicketExpanded from "./IncidentTicketExpanded.jsx";

const PRIORITIES = ["Low", "Medium", "Critical"];
const STATUSES = ["Open", "In-Progress", "Blocked", "Resolved", "Closed"];

/**
 * Lists accessible incident tickets and provides ticket conversation actions.
 *
 * @param {{onSuccess: (message: string) => void, refreshKey: number}} props Component props.
 * @returns {JSX.Element} Incident ticket grid and dialogs.
 */
export default function IncidentTicketsDataGrid({onSuccess, refreshKey}) {
    const {user} = useAuth();
    const isAdmin = ["Facility_Admin", "FA"].includes(user?.role);
    const isEngineer = ["Engineer", "ENG"].includes(user?.role);
    const [tickets, setTickets] = useState([]);
    const [engineers, setEngineers] = useState([]);
    const [ownEngineerId, setOwnEngineerId] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [createOpen, setCreateOpen] = useState(false);
    const [createError, setCreateError] = useState("");
    const [createSaving, setCreateSaving] = useState(false);
    const [createForm, setCreateForm] = useState({
        title: "",
        description: "",
        priority: "Medium",
        assigned_engineer_id: "",
    });
    const [activeTicket, setActiveTicket] = useState(null);
    const [editForm, setEditForm] = useState(null);
    const [notes, setNotes] = useState([]);
    const [notesLoading, setNotesLoading] = useState(false);
    const [notesError, setNotesError] = useState("");
    const [noteText, setNoteText] = useState("");
    const [attachmentUrls, setAttachmentUrls] = useState("");
    const [noteSaving, setNoteSaving] = useState(false);
    const [noteActionError, setNoteActionError] = useState("");
    const availableEngineers = engineers.filter((engineer) => engineer.status === "Available");

    const fetchData = useCallback(async () => {
        try {
            const requests = [apiClient.get("/incident-tickets")];
            if (isAdmin || isEngineer) requests.push(apiClient.get("/engineers"));
            if (isEngineer) requests.push(apiClient.get("/engineers/me"));
            const responses = await Promise.all(requests);
            setTickets(responses[0].data);
            let responseIndex = 1;
            if (isAdmin || isEngineer) {
                setEngineers(responses[responseIndex].data);
                responseIndex += 1;
            } else {
                setEngineers([]);
            }
            setOwnEngineerId(isEngineer ? responses[responseIndex].data.id : null);
            setError("");
        } catch (requestError) {
            setError(requestError.response?.data?.detail ?? "Could not load incident tickets.");
        } finally {
            setLoading(false);
        }
    }, [isAdmin, isEngineer]);

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
        setCreateForm({
            title: "",
            description: "",
            priority: "Medium",
            assigned_engineer_id: isAdmin ? "" : String(ownEngineerId ?? ""),
        });
        setCreateError("");
        setCreateOpen(true);
    };

    const createTicket = async () => {
        setCreateSaving(true);
        setCreateError("");
        try {
            const payload = {
                title: createForm.title.trim(),
                description: createForm.description.trim(),
                priority: createForm.priority,
            };
            if (isAdmin && createForm.assigned_engineer_id) {
                payload.assigned_engineer_id = Number(createForm.assigned_engineer_id);
            }
            await apiClient.post("/incident-tickets", payload);
            setCreateOpen(false);
            onSuccess("Incident ticket created.");
            await fetchData();
        } catch (requestError) {
            setCreateError(requestError.response?.data?.detail ?? "Could not create the ticket.");
        } finally {
            setCreateSaving(false);
        }
    };

    const openTicket = useCallback(async (ticket) => {
        setActiveTicket(ticket);
        setEditForm({
            title: ticket.title,
            description: ticket.description,
            priority: ticket.priority,
            status: ticket.status,
            assigned_engineer_id: ticket.assigned_engineer_id
                ? String(ticket.assigned_engineer_id)
                : "",
        });
        setNotes([]);
        setNotesError("");
        setNoteText("");
        setAttachmentUrls("");
        setNoteActionError("");
        setNotesLoading(true);
        try {
            const response = await apiClient.get("/ticket-notes");
            setNotes(response.data.filter((note) => note.incident_ticket_id === ticket.id));
        } catch (requestError) {
            setNotesError(requestError.response?.data?.detail ?? "Could not load ticket notes.");
        } finally {
            setNotesLoading(false);
        }
    }, []);

    const saveTicket = async () => {
        if (!activeTicket) return;
        const payload = isAdmin
            ? {
                title: editForm.title,
                description: editForm.description,
                priority: editForm.priority,
                status: editForm.status,
                assigned_engineer_id: editForm.assigned_engineer_id
                    ? Number(editForm.assigned_engineer_id)
                    : null,
            }
            : {priority: editForm.priority, status: editForm.status};
        try {
            const response = await apiClient.patch(`/incident-tickets/${activeTicket.id}`, payload);
            setTickets((current) => current.map((ticket) => (
                ticket.id === activeTicket.id ? response.data : ticket
            )));
            setActiveTicket(response.data);
            onSuccess("Incident ticket updated.");
        } catch (requestError) {
            setNoteActionError(requestError.response?.data?.detail ?? "Could not update the ticket.");
        }
    };

    const deleteTicket = async () => {
        if (!activeTicket) return;
        try {
            await apiClient.delete(`/incident-tickets/${activeTicket.id}`);
            setTickets((current) => current.filter((ticket) => ticket.id !== activeTicket.id));
            setActiveTicket(null);
            onSuccess("Incident ticket deleted.");
        } catch (requestError) {
            setNoteActionError(requestError.response?.data?.detail ?? "Could not delete the ticket.");
        }
    };

    const createNote = async () => {
        if (!activeTicket || !noteText.trim()) {
            setNoteActionError("Enter a message before posting.");
            return;
        }
        setNoteSaving(true);
        setNoteActionError("");
        try {
            const attachments = attachmentUrls
                .split(/\r?\n/)
                .map((url) => url.trim())
                .filter(Boolean)
                .map((file_url) => ({file_url}));
            const response = await apiClient.post("/ticket-notes", {
                incident_ticket_id: activeTicket.id,
                notes: noteText.trim(),
                attachments,
            });
            setNotes((current) => [...current, response.data]);
            setNoteText("");
            setAttachmentUrls("");
            onSuccess("Ticket note posted.");
        } catch (requestError) {
            setNoteActionError(requestError.response?.data?.detail ?? "Could not post the note.");
        } finally {
            setNoteSaving(false);
        }
    };

    const columns = useMemo(() => [
        {field: "id", headerName: "ID", width: 75},
        {field: "title", headerName: "Title", minWidth: 220, flex: 1},
        {
            field: "created_by_username",
            headerName: "Created By",
            minWidth: 160,
            valueGetter: (value) => value ?? "Unknown user",
        },
        {field: "priority", headerName: "Priority", minWidth: 110},
        {field: "status", headerName: "Status", minWidth: 130},
        {
            field: "assigned_engineer_id",
            headerName: "Assigned Engineer",
            minWidth: 175,
            valueGetter: (value) => (value
                ? engineers.find((engineer) => engineer.id === value)?.name ?? `Engineer #${value}`
                : "Unassigned"),
        },
        {
            field: "actions",
            headerName: "Ticket",
            width: 120,
            sortable: false,
            filterable: false,
            renderCell: ({row}) => (
                <Button size="small" onClick={() => openTicket(row)}>Open</Button>
            ),
        },
    ], [engineers, openTicket]);

    if (loading) return <CircularProgress aria-label="Loading incident tickets" />;
    if (error) return <Alert severity="error">{error}</Alert>;

    const canUpdateActiveTicket = Boolean(
        isAdmin || (isEngineer && activeTicket?.assigned_engineer_id === ownEngineerId)
    );

    return (
        <Box sx={{width: "100%"}}>
            <Button variant="outlined" sx={{mb: 2}} onClick={openCreateDialog}>
                Create Incident Ticket
            </Button>
            <DataGrid
                rows={tickets}
                columns={columns}
                autoHeight
                disableRowSelectionOnClick
                pageSizeOptions={[5, 10, 25]}
                initialState={{pagination: {paginationModel: {pageSize: 10}}}}
            />
            <Dialog open={createOpen} onClose={() => !createSaving && setCreateOpen(false)} fullWidth>
                <DialogTitle>Create Incident Ticket</DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{mt: 1}}>
                        {createError && <Alert severity="error">{createError}</Alert>}
                        <TextField
                            required
                            label="Title"
                            inputProps={{maxLength: 50}}
                            value={createForm.title}
                            onChange={(event) => setCreateForm({...createForm, title: event.target.value})}
                        />
                        <TextField
                            required
                            multiline
                            minRows={3}
                            label="Description"
                            value={createForm.description}
                            onChange={(event) => setCreateForm({...createForm, description: event.target.value})}
                        />
                        <TextField
                            select
                            label="Priority"
                            value={createForm.priority}
                            onChange={(event) => setCreateForm({...createForm, priority: event.target.value})}
                        >
                            {PRIORITIES.map((priority) => <MenuItem key={priority} value={priority}>{priority}</MenuItem>)}
                        </TextField>
                        {isAdmin && (
                            <TextField
                                select
                                label="Assigned engineer (optional)"
                                value={createForm.assigned_engineer_id}
                                onChange={(event) => setCreateForm({...createForm, assigned_engineer_id: event.target.value})}
                            >
                                <MenuItem value="">Unassigned</MenuItem>
                                {availableEngineers.map((engineer) => (
                                    <MenuItem key={engineer.id} value={engineer.id}>
                                        {engineer.name}
                                    </MenuItem>
                                ))}
                            </TextField>
                        )}
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setCreateOpen(false)} disabled={createSaving}>Cancel</Button>
                    <Button
                        variant="contained"
                        onClick={createTicket}
                        disabled={createSaving || !createForm.title.trim() || !createForm.description.trim()}
                    >
                        Create
                    </Button>
                </DialogActions>
            </Dialog>
            <Dialog open={Boolean(activeTicket)} onClose={() => setActiveTicket(null)} fullWidth maxWidth="md">
                <DialogTitle>Ticket {activeTicket?.id}: {activeTicket?.title}</DialogTitle>
                <DialogContent dividers>
                    <Stack spacing={2}>
                        {noteActionError && <Alert severity="error">{noteActionError}</Alert>}
                        {canUpdateActiveTicket && (
                            <>
                                {isAdmin && (
                                    <>
                                        <TextField
                                            label="Title"
                                            value={editForm?.title ?? ""}
                                            onChange={(event) => setEditForm({...editForm, title: event.target.value})}
                                        />
                                        <TextField
                                            multiline
                                            minRows={2}
                                            label="Description"
                                            value={editForm?.description ?? ""}
                                            onChange={(event) => setEditForm({...editForm, description: event.target.value})}
                                        />
                                    </>
                                )}
                                <Stack direction={{xs: "column", sm: "row"}} spacing={2}>
                                    <TextField
                                        select
                                        fullWidth
                                        label="Status"
                                        value={editForm?.status ?? ""}
                                        onChange={(event) => setEditForm({...editForm, status: event.target.value})}
                                    >
                                        {STATUSES.map((status) => <MenuItem key={status} value={status}>{status}</MenuItem>)}
                                    </TextField>
                                    <TextField
                                        select
                                        fullWidth
                                        label="Priority"
                                        value={editForm?.priority ?? ""}
                                        onChange={(event) => setEditForm({...editForm, priority: event.target.value})}
                                    >
                                        {PRIORITIES.map((priority) => <MenuItem key={priority} value={priority}>{priority}</MenuItem>)}
                                    </TextField>
                                </Stack>
                                {isAdmin && (
                                    <TextField
                                        select
                                        label="Assigned engineer"
                                        value={editForm?.assigned_engineer_id ?? ""}
                                        onChange={(event) => setEditForm({...editForm, assigned_engineer_id: event.target.value})}
                                    >
                                        <MenuItem value="">Unassigned</MenuItem>
                                        {availableEngineers.map((engineer) => (
                                            <MenuItem key={engineer.id} value={engineer.id}>{engineer.name}</MenuItem>
                                        ))}
                                        {engineers
                                            .filter((engineer) => (
                                                engineer.id === Number(editForm?.assigned_engineer_id)
                                                && engineer.status !== "Available"
                                            ))
                                            .map((engineer) => (
                                                <MenuItem key={engineer.id} value={engineer.id} disabled>
                                                    {engineer.name} (Unavailable — currently assigned)
                                                </MenuItem>
                                            ))}
                                    </TextField>
                                )}
                                <Button variant="contained" onClick={saveTicket}>Save Ticket Changes</Button>
                            </>
                        )}
                        <IncidentTicketExpanded
                            ticket={activeTicket}
                            notes={notes}
                            notesLoading={notesLoading}
                            notesError={notesError}
                        />
                        <TextField
                            multiline
                            minRows={3}
                            label="Add a note"
                            value={noteText}
                            onChange={(event) => setNoteText(event.target.value)}
                        />
                        <TextField
                            multiline
                            minRows={2}
                            label="Attachment URLs (one per line)"
                            value={attachmentUrls}
                            onChange={(event) => setAttachmentUrls(event.target.value)}
                            helperText="Paste accessible file URLs; file uploads are not configured here."
                        />
                        <Button
                            variant="outlined"
                            onClick={createNote}
                            disabled={noteSaving || !noteText.trim()}
                        >
                            Post Note
                        </Button>
                    </Stack>
                </DialogContent>
                <DialogActions>
                    {isAdmin && (
                        <Button color="error" onClick={deleteTicket}>Delete Ticket</Button>
                    )}
                    <Button onClick={() => setActiveTicket(null)}>Close</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}

IncidentTicketsDataGrid.propTypes = {
    onSuccess: PropTypes.func,
    refreshKey: PropTypes.number,
};

IncidentTicketsDataGrid.defaultProps = {
    onSuccess: () => {},
    refreshKey: 0,
};