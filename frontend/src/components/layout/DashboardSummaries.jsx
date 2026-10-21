import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
    Alert,
    Box,
    Card,
    CardContent,
    CircularProgress,
    Grid,
    Stack,
    Typography,
    useTheme,
} from "@mui/material";
import apiClient from "../../api/client.js";
import { useAuth } from "../../services/AuthContext.jsx";

const STATUS_ORDER = ["Open", "In-Progress", "Blocked", "Resolved", "Closed"];

function getChartColor(theme, index) {
    const palette = [
        theme.palette.primary.main,
        theme.palette.secondary.main,
        theme.palette.success.main,
        theme.palette.warning.main,
        theme.palette.error.main,
        theme.palette.info.main,
    ];
    return palette[index % palette.length];
}

function formatDuration(milliseconds) {
    const totalMinutes = Math.round(milliseconds / 60_000);
    if (totalMinutes < 1) return "Under 1 min";
    const days = Math.floor(totalMinutes / (60 * 24));
    const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
    const minutes = totalMinutes % 60;
    const parts = [];
    if (days) parts.push(`${days}d`);
    if (hours) parts.push(`${hours}h`);
    if (minutes && days === 0) parts.push(`${minutes}m`);
    return parts.join(" ");
}

function averageDuration(tickets, startField, endField) {
    const durations = tickets
        .map((ticket) => {
            const start = Date.parse(ticket[startField]);
            const end = Date.parse(ticket[endField]);
            return Number.isFinite(start) && Number.isFinite(end) && end >= start
                ? end - start
                : null;
        })
        .filter((duration) => duration !== null);
    if (!durations.length) return null;
    return durations.reduce((total, duration) => total + duration, 0) / durations.length;
}

function SummaryCard({title, value, description}) {
    return (
        <Card variant="outlined" sx={{height: "100%"}}>
            <CardContent>
                <Typography color="text.secondary" variant="subtitle2">{title}</Typography>
                <Typography variant="h4" sx={{my: 1}}>{value}</Typography>
                <Typography color="text.secondary" variant="body2">{description}</Typography>
            </CardContent>
        </Card>
    );
}

SummaryCard.propTypes = {
    description: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    value: PropTypes.string.isRequired,
};

/**
 * Displays role-scoped ticket metrics and admin-only facility location rankings.
 *
 * Lifecycle durations are averaged only when both event timestamps are present
 * and occur in chronological order.
 *
 * @param {{refreshKey: number}} props Component props.
 * @returns {JSX.Element} Ticket and facility dashboard summaries.
 */
export default function DashboardSummaries({refreshKey}) {
    const {user} = useAuth();
    const isAdmin = ["Facility_Admin", "FA"].includes(user?.role);
    const [tickets, setTickets] = useState([]);
    const [buildings, setBuildings] = useState([]);
    const [floors, setFloors] = useState([]);
    const [seats, setSeats] = useState([]);
    const [userCounts, setUserCounts] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        let cancelled = false;
        const requests = [
            apiClient.get("/incident-tickets"),
            apiClient.get("/users/dashboard-counts"),
        ];
        if (isAdmin) {
            requests.push(
                apiClient.get("/buildings"),
                apiClient.get("/floors"),
                apiClient.get("/seats"),
            );
        }
        Promise.resolve()
            .then(() => Promise.all(requests))
            .then((responses) => {
                if (cancelled) return;
                setTickets(responses[0].data);
                setUserCounts(responses[1].data);
                if (isAdmin) {
                    setBuildings(responses[2].data);
                    setFloors(responses[3].data);
                    setSeats(responses[4].data);
                } else {
                    setBuildings([]);
                    setFloors([]);
                    setSeats([]);
                }
                setError("");
            })
            .catch((requestError) => {
                if (!cancelled) {
                    setError(requestError.response?.data?.detail ?? "Could not load dashboard data.");
                }
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => {
            cancelled = true;
        };
    }, [isAdmin, refreshKey]);

    const metrics = useMemo(() => {
        const total = tickets.length;
        const byStatus = new Map(STATUS_ORDER.map((status) => [status, 0]));
        const byPriority = new Map();
        tickets.forEach((ticket) => {
            byStatus.set(ticket.status, (byStatus.get(ticket.status) ?? 0) + 1);
            byPriority.set(ticket.priority, (byPriority.get(ticket.priority) ?? 0) + 1);
        });
        return {
            total,
            averageTimeToAcknowledgement: averageDuration(
                tickets,
                "created_at",
                "acknowledged_at",
            ),
            averageAcknowledgementToAssignment: averageDuration(
                tickets,
                "acknowledged_at",
                "assigned_at",
            ),
            averageAssignmentToCompletion: averageDuration(
                tickets,
                "assigned_at",
                "completed_at",
            ),
            byStatus: [...byStatus.entries()].map(([label, count]) => ({label, count})),
            byPriority: [...byPriority.entries()].map(([label, count]) => ({label, count})),
        };
    }, [tickets]);

    const rankings = useMemo(() => {
        const floorsById = new Map(floors.map((floor) => [floor.id, floor]));
        const buildingsById = new Map(buildings.map((building) => [building.id, building]));
        const ticketsByCreator = new Map();
        tickets.forEach((ticket) => {
            ticketsByCreator.set(
                ticket.created_by_id,
                (ticketsByCreator.get(ticket.created_by_id) ?? 0) + 1,
            );
        });

        const rankedSeats = seats.map((seat) => {
            const floor = floorsById.get(seat.floor_id);
            const building = floor ? buildingsById.get(floor.building_id) : null;
            return {
                ...seat,
                floor,
                building,
                count: seat.occupied_by == null
                    ? 0
                    : ticketsByCreator.get(seat.occupied_by) ?? 0,
            };
        });
        const seatRankings = rankedSeats
            .filter((seat) => seat.count > 0)
            .sort((left, right) => right.count - left.count || left.seat_id.localeCompare(right.seat_id))
            .slice(0, 5)
            .map((seat) => ({
                id: seat.id,
                count: seat.count,
                label: `${seat.seat_id} · ${seat.building?.name ?? "Facility"} / Floor ${seat.floor?.floor_id ?? "?"}`,
            }));

        const ticketsByFloor = new Map();
        const ticketsByBuilding = new Map();
        rankedSeats.forEach((seat) => {
            if (!seat.floor || !seat.building) return;
            ticketsByFloor.set(
                seat.floor.id,
                (ticketsByFloor.get(seat.floor.id) ?? 0) + seat.count,
            );
            ticketsByBuilding.set(
                seat.building.id,
                (ticketsByBuilding.get(seat.building.id) ?? 0) + seat.count,
            );
        });
        const sortRanked = (entries) => entries
            .filter((item) => item.count > 0)
            .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label))
            .slice(0, 5);

        return {
            buildings: sortRanked(buildings.map((building) => ({
                id: building.id,
                label: building.name,
                count: ticketsByBuilding.get(building.id) ?? 0,
            }))),
            floors: sortRanked(floors.map((floor) => ({
                id: floor.id,
                label: `Floor ${floor.floor_id} · ${buildingsById.get(floor.building_id)?.name ?? "Facility"}`,
                count: ticketsByFloor.get(floor.id) ?? 0,
            }))),
            seats: seatRankings,
        };
    }, [buildings, floors, seats, tickets]);

    if (loading) return <CircularProgress aria-label="Loading dashboard summaries" />;
    if (error) return <Alert severity="error">{error}</Alert>;

    return (
        <Stack spacing={3}>
            <Box>
                <Typography variant="h5" component="h2">Dashboard</Typography>
                <Typography color="text.secondary">
                    Summary of {metrics.total} ticket{metrics.total === 1 ? "" : "s"} visible to your account.
                </Typography>
            </Box>
            <Grid container spacing={2}>
                <Grid size={{xs: 12, sm: 6, md: 3}}>
                    <SummaryCard
                        title="Avg. Time to Acknowledge"
                        value={metrics.averageTimeToAcknowledgement === null
                            ? "No data"
                            : formatDuration(metrics.averageTimeToAcknowledgement)}
                        description="Average time from ticket creation to first status change"
                    />
                </Grid>
                <Grid size={{xs: 12, sm: 6, md: 3}}>
                    <SummaryCard
                        title="Avg. Acknowledgement to Assignment"
                        value={metrics.averageAcknowledgementToAssignment === null
                            ? "No data"
                            : formatDuration(metrics.averageAcknowledgementToAssignment)}
                        description="Only tickets assigned after acknowledgement"
                    />
                </Grid>
                <Grid size={{xs: 12, sm: 6, md: 3}}>
                    <SummaryCard
                        title="Avg. Assignment to Completion"
                        value={metrics.averageAssignmentToCompletion === null
                            ? "No data"
                            : formatDuration(metrics.averageAssignmentToCompletion)}
                        description="Only tickets completed after assignment"
                    />
                </Grid>
                <Grid size={{xs: 12, sm: 6, md: 3}}>
                    <SummaryCard
                        title="Total Tickets"
                        value={String(metrics.total)}
                        description="Tickets visible to your account"
                    />
                </Grid>
            </Grid>
            <Grid container spacing={2}>
                <Grid size={{xs: 12, md: 6}}>
                    <ChartCard title="Tickets by Status" items={metrics.byStatus} />
                </Grid>
                <Grid size={{xs: 12, md: 6}}>
                    <ChartCard title="Tickets by Priority" items={metrics.byPriority} />
                </Grid>
            </Grid>
            {isAdmin && (
                <Box>
                    <Typography variant="h6" component="h2" sx={{mb: 1.5}}>
                        Ticket Volume by Facility Location
                    </Typography>
                    <Grid container spacing={2}>
                        <Grid size={{xs: 12, md: 4}}>
                            <RankingCard title="Buildings with Most Tickets" items={rankings.buildings} />
                        </Grid>
                        <Grid size={{xs: 12, md: 4}}>
                            <RankingCard title="Floors with Most Tickets" items={rankings.floors} />
                        </Grid>
                        <Grid size={{xs: 12, md: 4}}>
                            <RankingCard title="Seats with Most Tickets" items={rankings.seats} />
                        </Grid>
                    </Grid>
                </Box>
            )}
            <Box>
                <Typography variant="h6" component="h2" sx={{mb: 1.5}}>
                    User Statistics
                </Typography>
                <Grid container spacing={2}>
                    <Grid size={{xs: 12, sm: 6, md: isAdmin ? 4 : 6}}>
                        <SummaryCard
                            title="Employees"
                            value={String(userCounts?.employee_count ?? 0)}
                            description="Employee accounts"
                        />
                    </Grid>
                    <Grid size={{xs: 12, sm: 6, md: isAdmin ? 4 : 6}}>
                        <SummaryCard
                            title="Engineers"
                            value={String(userCounts?.engineer_count ?? 0)}
                            description="Engineer accounts"
                        />
                    </Grid>
                    {isAdmin && (
                        <Grid size={{xs: 12, sm: 6, md: 4}}>
                            <SummaryCard
                                title="Facility Admins"
                                value={String(userCounts?.facility_admin_count ?? 0)}
                                description="Facility administrator accounts"
                            />
                        </Grid>
                    )}
                </Grid>
            </Box>
        </Stack>
    );
}

/**
 * Draws a simple proportional bar chart for a ticket grouping.
 *
 * @param {{items: Array, title: string}} props Chart properties.
 * @returns {JSX.Element} Grouped ticket chart.
 */
function ChartCard({items, title}) {
    const theme = useTheme();
    const total = items.reduce((sum, item) => sum + item.count, 0);
    const radius = 72;
    const circumference = 2 * Math.PI * radius;
    const chartSegments = items.reduce((segments, item, index) => {
        const previousSegment = segments[segments.length - 1];
        const segment = total ? (item.count / total) * circumference : 0;
        return [
            ...segments,
            {
                item,
                index,
                offset: previousSegment
                    ? previousSegment.offset + previousSegment.length
                    : 0,
                length: segment,
            },
        ];
    }, []);
    return (
        <Card variant="outlined">
            <CardContent>
                <Typography variant="h6" sx={{mb: 2}}>{title}</Typography>
                {items.length ? (
                    <Stack
                        direction={{xs: "column", sm: "row"}}
                        spacing={3}
                        alignItems="center"
                    >
                        <Box
                            component="svg"
                            viewBox="0 0 200 200"
                            role="img"
                            aria-label={`${title}: ${items.map(({label, count}) => `${label} ${count}`).join(", ")}`}
                            sx={{width: 200, maxWidth: "100%", flexShrink: 0}}
                        >
                            <circle
                                cx="100"
                                cy="100"
                                r={radius}
                                fill="none"
                                stroke={theme.palette.action.hover}
                                strokeWidth="40"
                            />
                            {chartSegments.map(({item, index, length, offset: segmentOffset}) => (
                                    <circle
                                        key={item.label}
                                        cx="100"
                                        cy="100"
                                        r={radius}
                                        fill="none"
                                        stroke={getChartColor(theme, index)}
                                        strokeWidth="40"
                                        strokeDasharray={`${length} ${circumference - length}`}
                                        strokeDashoffset={-segmentOffset}
                                        transform="rotate(-90 100 100)"
                                    />
                            ))}
                            <text
                                x="100"
                                y="96"
                                textAnchor="middle"
                                fill={theme.palette.text.primary}
                                fontSize="24"
                                fontWeight="600"
                            >
                                {total}
                            </text>
                            <text
                                x="100"
                                y="118"
                                textAnchor="middle"
                                fill={theme.palette.text.secondary}
                                fontSize="11"
                            >
                                tickets
                            </text>
                        </Box>
                        <Stack spacing={1} sx={{width: "100%"}}>
                            {items.map((item, index) => (
                                <Stack
                                    key={item.label}
                                    direction="row"
                                    alignItems="center"
                                    spacing={1}
                                >
                                    <Box
                                        aria-hidden="true"
                                        sx={{
                                            width: 12,
                                            height: 12,
                                            borderRadius: "50%",
                                            flexShrink: 0,
                                            bgcolor: getChartColor(theme, index),
                                        }}
                                    />
                                    <Typography variant="body2" sx={{flexGrow: 1}}>
                                        {item.label}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        {item.count} ({total ? Math.round((item.count / total) * 100) : 0}%)
                                    </Typography>
                                </Stack>
                            ))}
                        </Stack>
                    </Stack>
                ) : (
                    <Typography color="text.secondary">No ticket data available.</Typography>
                )}
            </CardContent>
        </Card>
    );
}

ChartCard.propTypes = {
    items: PropTypes.arrayOf(PropTypes.shape({
        label: PropTypes.string.isRequired,
        count: PropTypes.number.isRequired,
    })).isRequired,
    title: PropTypes.string.isRequired,
};

/**
 * Displays ranked locations with their associated ticket counts.
 *
 * @param {{items: Array, title: string}} props Ranking properties.
 * @returns {JSX.Element} Ticket-location ranking.
 */
function RankingCard({items, title}) {
    return (
        <Card variant="outlined" sx={{height: "100%"}}>
            <CardContent>
                <Typography variant="subtitle1" sx={{mb: 1}}>{title}</Typography>
                {items.length ? (
                    <Stack spacing={1}>
                        {items.map((item, index) => (
                            <Stack
                                key={item.id}
                                direction="row"
                                justifyContent="space-between"
                                spacing={1}
                            >
                                <Typography variant="body2">
                                    {index + 1}. {item.label}
                                </Typography>
                                <Typography variant="body2" fontWeight="bold">{item.count}</Typography>
                            </Stack>
                        ))}
                    </Stack>
                ) : (
                    <Typography variant="body2" color="text.secondary">
                        No ticket activity associated with this location.
                    </Typography>
                )}
            </CardContent>
        </Card>
    );
}

RankingCard.propTypes = {
    items: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.number.isRequired,
        label: PropTypes.string.isRequired,
        count: PropTypes.number.isRequired,
    })).isRequired,
    title: PropTypes.string.isRequired,
};

DashboardSummaries.propTypes = {
    refreshKey: PropTypes.number,
};

DashboardSummaries.defaultProps = {
    refreshKey: 0,
};