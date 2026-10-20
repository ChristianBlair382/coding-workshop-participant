import { useEffect, useState } from "react";
import { DataGrid } from "@mui/x-data-grid";
import { Alert, Box, CircularProgress, Typography } from "@mui/material";
import apiClient from "../../api/client.js";

export default function RolesAndPermissionsDataGrid() {
    const [roles, setRoles] = useState([]);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;

        apiClient.get("/users/roles-permissions")
            .then((response) => {
                if (!cancelled) setRoles(response.data);
            })
            .catch(() => {
                if (!cancelled) {
                    setError("Could not load role permissions.");
                }
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });

        return () => {
            cancelled = true;
        };
    }, []);

    if (loading) return <CircularProgress aria-label="Loading role permissions" />;
    if (error) return <Alert severity="error">{error}</Alert>;

    return (
        <Box sx={{width: "100%"}}>
            <DataGrid
                aria-label="Roles and permissions"
                rows={roles.map(({role, permissions}) => ({
                    id: role,
                    role,
                    permissions,
                }))}
                columns={[
                    {
                        field: "role",
                        headerName: "Role",
                        minWidth: 200,
                        flex: 0.4,
                    },
                    {
                        field: "permissions",
                        headerName: "Permissions",
                        minWidth: 320,
                        flex: 1,
                        sortable: false,
                        valueGetter: (value) => value.map(({name}) => name).join(", "),
                        renderCell: ({value}) => (
                            <Typography sx={{whiteSpace: "normal", py: 1}}>
                                {value || "No permissions assigned"}
                            </Typography>
                        ),
                    },
                ]}
                autoHeight
                getRowHeight={() => "auto"}
                disableRowSelectionOnClick
                initialState={{
                    pagination: {
                        paginationModel: {pageSize: 5},
                    },
                }}
                pageSizeOptions={[5, 10]}
            />
        </Box>
    );
}