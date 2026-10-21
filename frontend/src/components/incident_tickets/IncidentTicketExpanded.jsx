import PropTypes from "prop-types";
import {
    Alert,
    Box,
    CircularProgress,
    Stack,
    Typography,
} from "@mui/material";

/**
 * Displays ticket creator details and the ticket's author-attributed conversation.
 *
 * @param {{notes: Array, notesError: string, notesLoading: boolean, ticket: object|null}} props Component props.
 * @returns {JSX.Element} Expanded ticket conversation.
 */
export default function IncidentTicketExpanded({
    notes,
    notesError,
    notesLoading,
    ticket,
}) {
    return (
        <Stack spacing={1.5}>
            {ticket && (
                <Typography variant="body2" color="text.secondary">
                    Created by {ticket.created_by_username ?? `User #${ticket.created_by_id}`}
                </Typography>
            )}
            <Typography variant="h6">Conversation</Typography>
            {notesLoading ? (
                <CircularProgress size={24} aria-label="Loading notes" />
            ) : notesError ? (
                <Alert severity="error">{notesError}</Alert>
            ) : notes.length ? (
                <Stack spacing={1}>
                    {notes.map((note) => (
                        <Box
                            key={note.id}
                            sx={{
                                p: 1.5,
                                border: 1,
                                borderColor: "divider",
                                borderRadius: 1,
                            }}
                        >
                            <Typography variant="caption" color="text.secondary">
                                {note.author_username ?? `User #${note.author_id}`}
                                {" · "}
                                {new Date(note.created_at).toLocaleString()}
                            </Typography>
                            <Typography sx={{whiteSpace: "pre-wrap"}}>{note.notes}</Typography>
                            {note.attachments?.map((attachment) => (
                                <Typography key={attachment.id} variant="body2">
                                    <a href={attachment.file_url} target="_blank" rel="noreferrer">
                                        {attachment.file_url}
                                    </a>
                                </Typography>
                            ))}
                        </Box>
                    ))}
                </Stack>
            ) : (
                <Typography color="text.secondary">No notes have been posted.</Typography>
            )}
        </Stack>
    );
}

IncidentTicketExpanded.propTypes = {
    notes: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.number.isRequired,
        author_id: PropTypes.number.isRequired,
        author_username: PropTypes.string,
        created_at: PropTypes.string.isRequired,
        notes: PropTypes.string,
        attachments: PropTypes.arrayOf(PropTypes.shape({
            id: PropTypes.number.isRequired,
            file_url: PropTypes.string.isRequired,
        })),
    })),
    notesError: PropTypes.string,
    notesLoading: PropTypes.bool,
    ticket: PropTypes.shape({
        created_by_id: PropTypes.number.isRequired,
        created_by_username: PropTypes.string,
    }),
};

IncidentTicketExpanded.defaultProps = {
    notes: [],
    notesError: "",
    notesLoading: false,
    ticket: null,
};