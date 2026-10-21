import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
    Autocomplete,
    Alert,
    Box,
    Button,
    Card,
    CardContent,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Grid,
    Stack,
    TextField,
    Typography,
} from "@mui/material";
import apiClient from "../../api/client.js";

/**
 * Displays buildings, floors, and seat occupancy as a facility overview.
 *
 * @param {{refreshKey: number}} props Component props.
 * @returns {JSX.Element} Building and seat map.
 */
export default function FacilityMap({buildingId, onSuccess, refreshKey}) {
    const [building, setBuilding] = useState(null);
    const [floors, setFloors] = useState([]);
    const [seats, setSeats] = useState([]);
    const [occupants, setOccupants] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [actionError, setActionError] = useState("");
    const [saving, setSaving] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [seatDialog, setSeatDialog] = useState(null);
    const [seatCount, setSeatCount] = useState("1");
    const [seatAssignments, setSeatAssignments] = useState([]);

    useEffect(() => {
        let cancelled = false;
        Promise.all([
            apiClient.get(`/buildings/${buildingId}`),
            apiClient.get("/floors"),
            apiClient.get("/seats"),
        ])
            .then(async ([buildingResponse, floorResponse, seatResponse]) => {
                if (cancelled) return;
                setBuilding(buildingResponse.data);
                setFloors(floorResponse.data);
                setSeats(seatResponse.data);
                const occupiedUserIds = [
                    ...new Set(
                        seatResponse.data
                            .map((seat) => seat.occupied_by)
                            .filter(Boolean),
                    ),
                ];
                if (occupiedUserIds.length) {
                    const params = new URLSearchParams();
                    occupiedUserIds.forEach((userId) => {
                        params.append("include_user_ids", userId);
                    });
                    const occupantResponse = await apiClient.get(
                        `/users/seat-assignment-options?${params.toString()}`,
                    );
                    if (cancelled) return;
                    setOccupants(Object.fromEntries(
                        occupantResponse.data.map((account) => [account.id, account]),
                    ));
                } else {
                    setOccupants({});
                }
                setError("");
            })
            .catch((requestError) => {
                if (!cancelled) {
                    setError(requestError.response?.data?.detail ?? "Could not load facility data.");
                }
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => {
            cancelled = true;
        };
    }, [buildingId, refreshKey]);

    const floorsByBuilding = useMemo(() => {
        const grouped = new Map();
        floors.forEach((floor) => {
            const buildingFloors = grouped.get(floor.building_id) ?? [];
            buildingFloors.push(floor);
            grouped.set(floor.building_id, buildingFloors);
        });
        grouped.forEach((buildingFloors) => buildingFloors.sort((a, b) => (
            a.floor_id.localeCompare(b.floor_id, undefined, {numeric: true})
        )));
        return grouped;
    }, [floors]);
    const buildingFloors = useMemo(
        () => (building ? floorsByBuilding.get(building.id) ?? [] : []),
        [building, floorsByBuilding],
    );
    const seatsByFloor = useMemo(() => {
        const grouped = new Map();
        seats.forEach((seat) => {
            const floorSeats = grouped.get(seat.floor_id) ?? [];
            floorSeats.push(seat);
            grouped.set(seat.floor_id, floorSeats);
        });
        grouped.forEach((floorSeats) => floorSeats.sort((a, b) => a.seat_id.localeCompare(b.seat_id)));
        return grouped;
    }, [seats]);
    const createFloor = async () => {
        setSaving(true);
        setActionError("");
        try {
            const existingFloorIds = new Set(buildingFloors.map((floor) => floor.floor_id));
            let floorNumber = 1;
            while (existingFloorIds.has(String(floorNumber))) floorNumber += 1;
            const response = await apiClient.post("/floors", {
                floor_id: String(floorNumber),
                seat_count: 0,
                building_id: building.id,
            });
            setFloors((current) => [...current, response.data]);
            onSuccess(`Floor ${response.data.floor_id} added to ${building.name}.`);
        } catch (requestError) {
            setActionError(requestError.response?.data?.detail ?? "Could not add a floor.");
        } finally {
            setSaving(false);
        }
    };

    const openCreateSeats = (floor) => {
        setSeatDialog({mode: "create", floor});
        setSeatCount("1");
        setSeatAssignments([null]);
        setActionError("");
    };

    const openSeatAssignment = (seat) => {
        setSeatDialog({mode: "assign", seat});
        setSeatCount("1");
        setSeatAssignments([occupants[seat.occupied_by] ?? null]);
        setActionError("");
    };

    const updateSeatAssignment = (index, user) => {
        setSeatAssignments((current) => current.map((assignment, itemIndex) => (
            itemIndex === index ? user : assignment
        )));
    };

    const saveSeatDialog = async () => {
        if (!seatDialog) return;
        setSaving(true);
        setActionError("");
        try {
            const selectedIds = seatAssignments
                .filter(Boolean)
                .map((account) => account.id);
            if (new Set(selectedIds).size !== selectedIds.length) {
                setActionError("Each user can only be assigned to one seat.");
                return;
            }

            if (seatDialog.mode === "create") {
                const response = await apiClient.post(
                    `/seats/floors/${seatDialog.floor.id}/bulk`,
                    {occupied_by: seatAssignments.map((account) => account?.id ?? null)},
                );
                setSeats((current) => [...current, ...response.data]);
                setOccupants((current) => ({
                    ...current,
                    ...Object.fromEntries(
                        seatAssignments
                            .filter(Boolean)
                            .map((account) => [account.id, account]),
                    ),
                }));
                onSuccess(
                    `${response.data.length} seat${response.data.length === 1 ? "" : "s"} added to floor ${seatDialog.floor.floor_id}.`,
                );
            } else {
                const seat = seatDialog.seat;
                const user = seatAssignments[0];
                const response = await apiClient.patch(`/seats/${seat.id}`, {
                    occupied_by: user?.id ?? null,
                });
                setSeats((current) => current.map((item) => (
                    item.id === seat.id ? response.data : item
                )));
                if (user) {
                    setOccupants((current) => ({...current, [user.id]: user}));
                }
                onSuccess(
                    user
                        ? `${user.username} assigned to seat ${seat.seat_id}.`
                        : `Seat ${seat.seat_id} is now unoccupied.`,
                );
            }
            setSeatDialog(null);
        } catch (requestError) {
            setActionError(
                requestError.response?.data?.detail ?? "Could not save the seat assignments.",
            );
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!deleteTarget) return;
        setSaving(true);
        setActionError("");
        try {
            if (deleteTarget.type === "floor") {
                await apiClient.delete(`/floors/${deleteTarget.item.id}`);
                setFloors((current) => current.filter(
                    (floor) => floor.id !== deleteTarget.item.id,
                ));
                setSeats((current) => current.filter(
                    (seat) => seat.floor_id !== deleteTarget.item.id,
                ));
                onSuccess(`Floor ${deleteTarget.item.floor_id} deleted.`);
            } else {
                await apiClient.delete(`/seats/${deleteTarget.item.id}`);
                setSeats((current) => current.filter(
                    (seat) => seat.id !== deleteTarget.item.id,
                ));
                onSuccess(`Seat ${deleteTarget.item.seat_id} deleted.`);
            }
            setDeleteTarget(null);
        } catch (requestError) {
            setActionError(requestError.response?.data?.detail ?? "Could not delete the selected item.");
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <CircularProgress aria-label="Loading facility map" />;
    if (error) return <Alert severity="error">{error}</Alert>;
    if (!building) return <Alert severity="info">This facility is no longer available.</Alert>;

    return (
        <Stack spacing={3}>
            {actionError && <Alert severity="error">{actionError}</Alert>}
            <Card variant="outlined">
                <CardContent>
                    <Stack
                        direction={{xs: "column", sm: "row"}}
                        justifyContent="space-between"
                        alignItems={{xs: "stretch", sm: "center"}}
                        spacing={1}
                        sx={{mb: 2}}
                    >
                        <Typography color="text.secondary">
                            {building.location} · {buildingFloors.length} floors
                        </Typography>
                        <Button variant="outlined" onClick={createFloor} disabled={saving}>
                            Add Floor
                        </Button>
                    </Stack>
                    <Stack spacing={2}>
                        {buildingFloors.map((floor) => {
                            const floorSeats = seatsByFloor.get(floor.id) ?? [];
                            return (
                                <Box key={floor.id}>
                                    <Stack
                                        direction="row"
                                        justifyContent="space-between"
                                        alignItems="center"
                                        sx={{mb: 1}}
                                    >
                                        <Typography variant="subtitle1">
                                            Floor {floor.floor_id} · {floorSeats.length} seats
                                        </Typography>
                                        <Stack direction="row" spacing={1}>
                                            <Button
                                                size="small"
                                                onClick={() => openCreateSeats(floor)}
                                                disabled={saving}
                                            >
                                                Add Seats
                                            </Button>
                                            <Button
                                                size="small"
                                                color="error"
                                                onClick={() => setDeleteTarget({
                                                    type: "floor",
                                                    item: floor,
                                                })}
                                                disabled={saving}
                                            >
                                                Delete Floor
                                            </Button>
                                        </Stack>
                                    </Stack>
                                    <Grid container spacing={1}>
                                        {floorSeats.map((seat) => {
                                            const occupant = occupants[seat.occupied_by];
                                            return (
                                                <Grid key={seat.id} size={{xs: 6, sm: 4, md: 3, lg: 2}}>
                                                    <Card
                                                        variant="outlined"
                                                        sx={{
                                                            borderColor: occupant ? "success.light" : "divider",
                                                            height: "100%",
                                                        }}
                                                    >
                                                        <CardContent sx={{p: 1.5, "&:last-child": {pb: 1.5}}}>
                                                            <Typography variant="subtitle2">{seat.seat_id}</Typography>
                                                            <Typography variant="caption" display="block" sx={{mt: 1}}>
                                                                {occupant ? occupant.username : seat.occupied_by ? "Assigned" : "Unassigned"}
                                                            </Typography>
                                                            <Button
                                                                size="small"
                                                                onClick={() => openSeatAssignment(seat)}
                                                                disabled={saving}
                                                                sx={{display: "block", mt: 0.5}}
                                                            >
                                                                Assign User
                                                            </Button>
                                                            <Button
                                                                size="small"
                                                                color="error"
                                                                onClick={() => setDeleteTarget({
                                                                    type: "seat",
                                                                    item: seat,
                                                                })}
                                                                disabled={saving}
                                                                sx={{display: "block", mt: 1}}
                                                            >
                                                                Delete Seat
                                                            </Button>
                                                        </CardContent>
                                                    </Card>
                                                </Grid>
                                            );
                                        })}
                                    </Grid>
                                </Box>
                            );
                        })}
                    </Stack>
                </CardContent>
            </Card>
            <Dialog
                open={Boolean(seatDialog)}
                onClose={() => !saving && setSeatDialog(null)}
                fullWidth
                maxWidth="sm"
            >
                <DialogTitle>
                    {seatDialog?.mode === "create"
                        ? `Add Seats to Floor ${seatDialog.floor.floor_id}`
                        : `Assign User to ${seatDialog?.seat.seat_id ?? "Seat"}`}
                </DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{mt: 1}}>
                        {actionError && <Alert severity="error">{actionError}</Alert>}
                        {seatDialog?.mode === "create" && (
                            <TextField
                                type="number"
                                label="Number of seats"
                                value={seatCount}
                                inputProps={{min: 1, max: 50, step: 1}}
                                onChange={(event) => {
                                    const count = Number(event.target.value);
                                    setSeatCount(event.target.value);
                                    if (Number.isInteger(count) && count >= 1 && count <= 50) {
                                        setSeatAssignments((current) => (
                                            Array.from(
                                                {length: count},
                                                (_, index) => current[index] ?? null,
                                            )
                                        ));
                                    }
                                }}
                                helperText="You can optionally assign one user to each new seat."
                            />
                        )}
                        {seatAssignments.map((account, index) => (
                            <SeatUserAutocomplete
                                key={`${seatDialog?.mode}-${seatDialog?.seat?.id ?? seatDialog?.floor?.id}-${index}`}
                                label={seatDialog?.mode === "create"
                                    ? `Seat ${index + 1} user`
                                    : "User (Leave blank to unassign)"}
                                user={account}
                                excludeUserIds={seatAssignments
                                    .filter((item, itemIndex) => item && itemIndex !== index)
                                    .map((item) => item.id)}
                                onChange={(selectedUser) => updateSeatAssignment(index, selectedUser)}
                            />
                        ))}
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setSeatDialog(null)} disabled={saving}>
                        Cancel
                    </Button>
                    <Button
                        variant="contained"
                        onClick={saveSeatDialog}
                        disabled={
                            saving
                            || (seatDialog?.mode === "create"
                                && (!Number.isInteger(Number(seatCount))
                                    || Number(seatCount) < 1
                                    || Number(seatCount) > 50))
                        }
                    >
                        {seatDialog?.mode === "create" ? "Create Seats" : "Save Assignment"}
                    </Button>
                </DialogActions>
            </Dialog>
            <Dialog
                open={Boolean(deleteTarget)}
                onClose={() => !saving && setDeleteTarget(null)}
            >
                <DialogTitle>
                    Delete {deleteTarget?.type === "floor" ? "Floor" : "Seat"}?
                </DialogTitle>
                <DialogContent>
                    {actionError && <Alert severity="error" sx={{mb: 2}}>{actionError}</Alert>}
                    <Typography>
                        {deleteTarget?.type === "floor"
                            ? `Delete floor ${deleteTarget.item.floor_id} and all of its seats?`
                            : `Delete seat ${deleteTarget?.item.seat_id}?`}
                        {" "}This action cannot be undone.
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteTarget(null)} disabled={saving}>
                        Cancel
                    </Button>
                    <Button
                        color="error"
                        variant="contained"
                        onClick={handleDelete}
                        disabled={saving}
                    >
                        Delete
                    </Button>
                </DialogActions>
            </Dialog>
        </Stack>
    );
}

/**
 * Searches available users from the server and selects an optional occupant.
 *
 * @param {{excludeUserIds: number[], label: string, onChange: (user: object|null) => void, user: object|null}} props Component props.
 * @returns {JSX.Element} Searchable user selector.
 */
function SeatUserAutocomplete({excludeUserIds, label, onChange, user}) {
    const [options, setOptions] = useState(user ? [user] : []);
    const [inputValue, setInputValue] = useState("");
    const [loadingOptions, setLoadingOptions] = useState(false);
    const [searchError, setSearchError] = useState("");

    useEffect(() => {
        const trimmedQuery = inputValue.trim();
        if (trimmedQuery.length < 2) return undefined;

        let cancelled = false;
        const timer = setTimeout(async () => {
            setLoadingOptions(true);
            setSearchError("");
            try {
                const response = await apiClient.get("/users/seat-assignment-options", {
                    params: {
                        query: trimmedQuery,
                    },
                });
                if (!cancelled) {
                    const merged = new Map(
                        [...(user ? [user] : []), ...response.data]
                            .map((account) => [account.id, account]),
                    );
                    setOptions([...merged.values()]);
                }
            } catch (requestError) {
                if (!cancelled) {
                    setSearchError(
                        requestError.response?.data?.detail ?? "Could not search users.",
                    );
                }
            } finally {
                if (!cancelled) setLoadingOptions(false);
            }
        }, trimmedQuery.length >= 2 ? 250 : 0);

        return () => {
            cancelled = true;
            clearTimeout(timer);
        };
    }, [inputValue, user]);

    const visibleOptions = options.filter((option) => (
        option.id === user?.id || !excludeUserIds.includes(option.id)
    ));

    return (
        <Autocomplete
            options={visibleOptions}
            value={user ?? null}
            loading={loadingOptions}
            filterOptions={(items) => items}
            getOptionLabel={(option) => option.username}
            isOptionEqualToValue={(option, value) => option.id === value.id}
            onChange={(_, selectedUser) => onChange(selectedUser)}
            inputValue={inputValue}
            onInputChange={(_, value, reason) => {
                if (reason === "input" || reason === "clear") setInputValue(value);
            }}
            noOptionsText={inputValue.trim().length < 2
                ? "Type at least 2 characters to search"
                : "No available users found"}
            renderInput={(params) => (
            <TextField
                {...params}
                label={label}
                placeholder="Search username"
                error={Boolean(searchError)}
                helperText={searchError || undefined}
            />
            )}
        />
    );
}

SeatUserAutocomplete.propTypes = {
    excludeUserIds: PropTypes.arrayOf(PropTypes.number),
    label: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
    user: PropTypes.shape({
        id: PropTypes.number.isRequired,
        username: PropTypes.string.isRequired,
    }),
};

SeatUserAutocomplete.defaultProps = {
    excludeUserIds: [],
    user: null,
};

FacilityMap.propTypes = {
    buildingId: PropTypes.number.isRequired,
    onSuccess: PropTypes.func,
    refreshKey: PropTypes.number,
};

FacilityMap.defaultProps = {
    onSuccess: () => {},
    refreshKey: 0,
};