import { zodResolver } from "@hookform/resolvers/zod";
import { AddOutlined, CalendarMonthOutlined, EditOutlined, ViewListOutlined } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { authApi } from "../auth/api";
import { clinicianApi } from "../clinicians/api";
import { patientApi } from "../patients/api";
import { Appointment, AppointmentInput, AppointmentStatus, appointmentApi } from "./api";

const statuses: AppointmentStatus[] = ["scheduled", "confirmed", "completed", "cancelled", "no_show"];
const appointmentSchema = z
  .object({
    patient_id: z.string().min(1),
    clinician_id: z.string().min(1),
    start_at: z.string().min(1),
    end_at: z.string().min(1),
    status: z.enum(statuses),
    reason: z.string().max(250),
    internal_notes: z.string().optional(),
  })
  .refine((value) => new Date(value.end_at) > new Date(value.start_at), { path: ["end_at"] });

const emptyAppointment: AppointmentInput = {
  patient_id: "",
  clinician_id: "",
  start_at: "",
  end_at: "",
  status: "scheduled",
  reason: "",
  internal_notes: "",
};

function toLocalDateTime(value: string) {
  return value ? dayjs(value).format("YYYY-MM-DDTHH:mm") : "";
}

function AppointmentDialog({
  open,
  appointment,
  canSeeInternalNotes,
  onClose,
}: {
  open: boolean;
  appointment: Appointment | null;
  canSeeInternalNotes: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const patients = useQuery({
    queryKey: ["patient-options"],
    queryFn: () => patientApi.list("", 1, 100),
    enabled: open,
  });
  const clinicians = useQuery({
    queryKey: ["clinician-options"],
    queryFn: () => clinicianApi.list(),
    enabled: open,
  });
  const form = useForm<AppointmentInput>({
    resolver: zodResolver(appointmentSchema),
    defaultValues: emptyAppointment,
  });
  useEffect(() => {
    form.reset(
      appointment
        ? {
            patient_id: appointment.patient.public_id,
            clinician_id: appointment.clinician.public_id,
            start_at: toLocalDateTime(appointment.start_at),
            end_at: toLocalDateTime(appointment.end_at),
            status: appointment.status,
            reason: appointment.reason,
            internal_notes: appointment.internal_notes ?? "",
          }
        : emptyAppointment,
    );
  }, [appointment, form, open]);
  const mutation = useMutation({
    mutationFn: (values: AppointmentInput) => {
      const payload = {
        ...values,
        start_at: new Date(values.start_at).toISOString(),
        end_at: new Date(values.end_at).toISOString(),
      };
      return appointment
        ? appointmentApi.update(appointment.public_id, payload)
        : appointmentApi.create(payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["appointments"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      onClose();
    },
  });
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <Box component="form" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <DialogTitle>{appointment ? t("editAppointment") : t("addAppointment")}</DialogTitle>
        <DialogContent>
          <Box display="grid" gridTemplateColumns={{ xs: "1fr", md: "1fr 1fr" }} gap={2} pt={1}>
            <TextField select label={t("patient")} defaultValue="" error={Boolean(form.formState.errors.patient_id)} {...form.register("patient_id")}>
              {patients.data?.results.map((patient) => (
                <MenuItem key={patient.public_id} value={patient.public_id}>{patient.first_name} {patient.last_name}</MenuItem>
              ))}
            </TextField>
            <TextField select label={t("clinician")} defaultValue="" error={Boolean(form.formState.errors.clinician_id)} {...form.register("clinician_id")}>
              {clinicians.data?.results.map((clinician) => (
                <MenuItem key={clinician.public_id} value={clinician.public_id}>
                  {clinician.first_name} {clinician.last_name}{clinician.specialty ? ` — ${clinician.specialty}` : ""}
                </MenuItem>
              ))}
            </TextField>
            <TextField label={t("startTime")} type="datetime-local" slotProps={{ inputLabel: { shrink: true } }} error={Boolean(form.formState.errors.start_at)} {...form.register("start_at")} />
            <TextField label={t("endTime")} type="datetime-local" slotProps={{ inputLabel: { shrink: true } }} error={Boolean(form.formState.errors.end_at)} {...form.register("end_at")} />
            <TextField select label={t("status")} defaultValue="scheduled" {...form.register("status")}>
              {statuses.map((statusValue) => <MenuItem key={statusValue} value={statusValue}>{t(statusValue)}</MenuItem>)}
            </TextField>
            <TextField label={t("reason")} {...form.register("reason")} />
            {canSeeInternalNotes && (
              <TextField label={t("internalNotes")} multiline minRows={3} sx={{ gridColumn: { md: "1 / -1" } }} {...form.register("internal_notes")} />
            )}
          </Box>
          {(mutation.isError || patients.isError || clinicians.isError) && (
            <Alert severity="error" sx={{ mt: 2 }}>{t("appointmentSaveError")}</Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>{t("cancel")}</Button>
          <Button type="submit" variant="contained" disabled={mutation.isPending}>{t("save")}</Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
}

export function AppointmentPage() {
  const { t, i18n } = useTranslation();
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null);
  const [viewMode, setViewMode] = useState<"table" | "calendar">("table");
  const session = useQuery({ queryKey: ["session"], queryFn: authApi.me });
  const appointments = useQuery({
    queryKey: ["appointments", statusFilter, page],
    queryFn: () => appointmentApi.list(statusFilter, page),
  });
  const groups = session.data?.groups ?? [];
  const isSuperUser = session.data?.is_superuser ?? false;
  const canEdit = isSuperUser || groups.some((group) => ["Admin", "Doctor", "Nurse", "Secretary"].includes(group));
  const canSeeInternalNotes = isSuperUser || groups.some((group) => ["Admin", "Doctor", "Nurse"].includes(group));
  const dateFormatter = new Intl.DateTimeFormat(i18n.resolvedLanguage ?? "tr", {
    dateStyle: "medium",
    timeStyle: "short",
  });
  const statusColor = (status: AppointmentStatus) => {
    if (status === "completed") return "success";
    if (status === "cancelled" || status === "no_show") return "default";
    return status === "confirmed" ? "primary" : "warning";
  };
  const openNew = () => { setSelectedAppointment(null); setDialogOpen(true); };
  const openEdit = (appointment: Appointment) => { setSelectedAppointment(appointment); setDialogOpen(true); };
  const groupedAppointments = (appointments.data?.results ?? []).reduce<Record<string, Appointment[]>>(
    (groupsByDate, appointment) => {
      const key = dayjs(appointment.start_at).format("YYYY-MM-DD");
      groupsByDate[key] = [...(groupsByDate[key] ?? []), appointment];
      return groupsByDate;
    },
    {},
  );

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
        <Box>
          <Typography variant="h4">{t("appointments")}</Typography>
          <Typography color="text.secondary">{t("appointmentManagementDescription")}</Typography>
        </Box>
        {canEdit && <Button variant="contained" startIcon={<AddOutlined />} onClick={openNew}>{t("addAppointment")}</Button>}
      </Stack>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
        <TextField
          select
          label={t("status")}
          value={statusFilter}
          onChange={(event) => { setStatusFilter(event.target.value); setPage(1); }}
          sx={{ width: { xs: "100%", sm: 260 } }}
        >
          <MenuItem value="">{t("allStatuses")}</MenuItem>
          {statuses.map((statusValue) => <MenuItem key={statusValue} value={statusValue}>{t(statusValue)}</MenuItem>)}
        </TextField>
        <ToggleButtonGroup exclusive value={viewMode} onChange={(_, value) => value && setViewMode(value)} size="small">
          <ToggleButton value="table" aria-label={t("tableView")}><ViewListOutlined sx={{ mr: 1 }} />{t("tableView")}</ToggleButton>
          <ToggleButton value="calendar" aria-label={t("calendarView")}><CalendarMonthOutlined sx={{ mr: 1 }} />{t("calendarView")}</ToggleButton>
        </ToggleButtonGroup>
      </Stack>
      {appointments.isError && <Alert severity="error">{t("genericError")}</Alert>}
      {viewMode === "table" ? <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead><TableRow>
            <TableCell>{t("patient")}</TableCell><TableCell>{t("clinician")}</TableCell>
            <TableCell>{t("startTime")}</TableCell><TableCell>{t("endTime")}</TableCell>
            <TableCell>{t("status")}</TableCell><TableCell>{t("reason")}</TableCell>
            {canEdit && <TableCell align="right">{t("actions")}</TableCell>}
          </TableRow></TableHead>
          <TableBody>
            {appointments.data?.results.map((appointment) => (
              <TableRow key={appointment.public_id} hover>
                <TableCell>{appointment.patient.first_name} {appointment.patient.last_name}</TableCell>
                <TableCell>{appointment.clinician.display_name || "—"}</TableCell>
                <TableCell>{dateFormatter.format(new Date(appointment.start_at))}</TableCell>
                <TableCell>{dateFormatter.format(new Date(appointment.end_at))}</TableCell>
                <TableCell><Chip size="small" color={statusColor(appointment.status)} label={t(appointment.status)} /></TableCell>
                <TableCell>{appointment.reason || "—"}</TableCell>
                {canEdit && <TableCell align="right"><IconButton aria-label={t("editAppointment")} onClick={() => openEdit(appointment)}><EditOutlined /></IconButton></TableCell>}
              </TableRow>
            ))}
            {!appointments.isPending && appointments.data?.results.length === 0 && (
              <TableRow><TableCell colSpan={7} align="center">{t("noAppointments")}</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer> : (
        <Stack spacing={2}>
          {Object.entries(groupedAppointments).map(([date, dateAppointments]) => (
            <Card key={date} variant="outlined">
              <CardContent>
                <Typography variant="h6" mb={1}>{new Intl.DateTimeFormat(i18n.resolvedLanguage ?? "tr", { dateStyle: "full" }).format(new Date(`${date}T12:00:00`))}</Typography>
                <Stack spacing={1}>
                  {dateAppointments.map((appointment) => (
                    <Stack key={appointment.public_id} direction={{ xs: "column", sm: "row" }} alignItems={{ sm: "center" }} gap={1}>
                      <Typography fontWeight={700}>{dayjs(appointment.start_at).format("HH:mm")}</Typography>
                      <Typography sx={{ flexGrow: 1 }}>{appointment.patient.first_name} {appointment.patient.last_name} · {appointment.clinician.display_name}</Typography>
                      <Chip size="small" color={statusColor(appointment.status)} label={t(appointment.status)} />
                      {canEdit && <IconButton aria-label={t("editAppointment")} onClick={() => openEdit(appointment)}><EditOutlined /></IconButton>}
                    </Stack>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          ))}
          {!appointments.isPending && Object.keys(groupedAppointments).length === 0 && <Alert severity="info">{t("noAppointments")}</Alert>}
        </Stack>
      )}
      <Stack direction="row" justifyContent="flex-end" gap={1}>
        <Button disabled={!appointments.data?.previous} onClick={() => setPage((value) => value - 1)}>{t("previous")}</Button>
        <Button disabled={!appointments.data?.next} onClick={() => setPage((value) => value + 1)}>{t("next")}</Button>
      </Stack>
      <AppointmentDialog open={dialogOpen} appointment={selectedAppointment} canSeeInternalNotes={canSeeInternalNotes} onClose={() => setDialogOpen(false)} />
    </Stack>
  );
}

