import { zodResolver } from "@hookform/resolvers/zod";
import { AddOutlined, EditOutlined, SearchOutlined, VisibilityOutlined } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  InputAdornment,
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
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { authApi } from "../auth/api";
import { Patient, PatientInput, patientApi } from "./api";

const patientSchema = z.object({
  first_name: z.string().min(2),
  last_name: z.string().min(2),
  birth_date: z.string().min(1),
  gender: z.enum(["female", "male", "non_binary", "other", "undisclosed", ""]),
  email: z.union([z.email(), z.literal("")]),
  phone: z.string(),
  address: z.string(),
  country_code: z.string().max(2),
  preferred_language: z.enum(["tr", "en"]),
  emergency_contact_name: z.string(),
  emergency_contact_phone: z.string(),
  allergies: z.string().optional(),
  clinical_notes: z.string().optional(),
  is_active: z.boolean(),
});

const emptyPatient: PatientInput = {
  first_name: "",
  last_name: "",
  birth_date: "",
  gender: "",
  email: "",
  phone: "",
  address: "",
  country_code: "",
  preferred_language: "tr",
  emergency_contact_name: "",
  emergency_contact_phone: "",
  allergies: "",
  clinical_notes: "",
  is_active: true,
};

function PatientDetailsDialog({ patient, onClose }: { patient: Patient | null; onClose: () => void }) {
  const { t } = useTranslation();
  const details = patient
    ? [
        [t("fullName"), `${patient.first_name} ${patient.last_name}`],
        [t("birthDate"), patient.birth_date],
        [t("email"), patient.email || "—"],
        [t("phone"), patient.phone || "—"],
        [t("address"), patient.address || "—"],
        [t("emergencyContact"), patient.emergency_contact_name || "—"],
        [t("emergencyPhone"), patient.emergency_contact_phone || "—"],
        ...(patient.allergies !== undefined ? [[t("allergies"), patient.allergies || "—"]] : []),
        ...(patient.clinical_notes !== undefined ? [[t("clinicalNotes"), patient.clinical_notes || "—"]] : []),
      ]
    : [];
  return (
    <Dialog open={Boolean(patient)} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{t("patientDetails")}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} pt={1}>
          {details.map(([label, value]) => (
            <Box key={label}>
              <Typography variant="caption" color="text.secondary">{label}</Typography>
              <Typography sx={{ whiteSpace: "pre-wrap" }}>{value}</Typography>
            </Box>
          ))}
        </Stack>
      </DialogContent>
      <DialogActions><Button onClick={onClose}>{t("close")}</Button></DialogActions>
    </Dialog>
  );
}

function PatientDialog({
  open,
  patient,
  canSeeClinicalFields,
  onClose,
}: {
  open: boolean;
  patient: Patient | null;
  canSeeClinicalFields: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const form = useForm<PatientInput>({ resolver: zodResolver(patientSchema), defaultValues: emptyPatient });
  useEffect(() => {
    form.reset(patient ? { ...emptyPatient, ...patient } : emptyPatient);
  }, [form, patient, open]);
  const mutation = useMutation({
    mutationFn: (values: PatientInput) =>
      patient ? patientApi.update(patient.public_id, values) : patientApi.create(values),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["patients"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      onClose();
    },
  });
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <Box component="form" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <DialogTitle>{patient ? t("editPatient") : t("addPatient")}</DialogTitle>
        <DialogContent>
          <Box display="grid" gridTemplateColumns={{ xs: "1fr", md: "1fr 1fr" }} gap={2} pt={1}>
            <TextField label={t("firstName")} error={Boolean(form.formState.errors.first_name)} {...form.register("first_name")} />
            <TextField label={t("lastName")} error={Boolean(form.formState.errors.last_name)} {...form.register("last_name")} />
            <TextField label={t("birthDate")} type="date" slotProps={{ inputLabel: { shrink: true } }} error={Boolean(form.formState.errors.birth_date)} {...form.register("birth_date")} />
            <TextField select label={t("gender")} defaultValue="" {...form.register("gender")}>
              <MenuItem value="">—</MenuItem>
              {(["female", "male", "non_binary", "other", "undisclosed"] as const).map((value) => (
                <MenuItem key={value} value={value}>{t(value)}</MenuItem>
              ))}
            </TextField>
            <TextField label={t("email")} type="email" {...form.register("email")} />
            <TextField label={t("phone")} {...form.register("phone")} />
            <TextField label={t("countryCode")} inputProps={{ maxLength: 2 }} {...form.register("country_code")} />
            <TextField select label={t("preferredLanguage")} defaultValue="tr" {...form.register("preferred_language")}>
              <MenuItem value="tr">Türkçe</MenuItem>
              <MenuItem value="en">English</MenuItem>
            </TextField>
            <TextField label={t("emergencyContact")} {...form.register("emergency_contact_name")} />
            <TextField label={t("emergencyPhone")} {...form.register("emergency_contact_phone")} />
            <TextField label={t("address")} multiline minRows={2} sx={{ gridColumn: { md: "1 / -1" } }} {...form.register("address")} />
            {canSeeClinicalFields && (
              <>
                <TextField label={t("allergies")} multiline minRows={2} {...form.register("allergies")} />
                <TextField label={t("clinicalNotes")} multiline minRows={2} {...form.register("clinical_notes")} />
              </>
            )}
          </Box>
          {mutation.isError && <Alert severity="error" sx={{ mt: 2 }}>{t("genericError")}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>{t("cancel")}</Button>
          <Button type="submit" variant="contained" disabled={mutation.isPending}>{t("save")}</Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
}

export function PatientPage() {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [viewedPatient, setViewedPatient] = useState<Patient | null>(null);
  const session = useQuery({ queryKey: ["session"], queryFn: authApi.me });
  const patients = useQuery({
    queryKey: ["patients", search, page],
    queryFn: () => patientApi.list(search, page),
  });
  const groups = session.data?.groups ?? [];
  const canEdit = groups.some((group) => ["Admin", "Doctor", "Nurse", "Secretary"].includes(group));
  const canSeeClinicalFields = groups.some((group) => ["Admin", "Doctor", "Nurse"].includes(group));

  const openNew = () => { setSelectedPatient(null); setDialogOpen(true); };
  const openEdit = (patient: Patient) => { setSelectedPatient(patient); setDialogOpen(true); };

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
        <Box>
          <Typography variant="h4">{t("patients")}</Typography>
          <Typography color="text.secondary">{t("patientManagementDescription")}</Typography>
        </Box>
        {canEdit && <Button variant="contained" startIcon={<AddOutlined />} onClick={openNew}>{t("addPatient")}</Button>}
      </Stack>
      <TextField
        value={search}
        onChange={(event) => { setSearch(event.target.value); setPage(1); }}
        placeholder={t("searchPatients")}
        sx={{ maxWidth: 420 }}
        slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchOutlined /></InputAdornment> } }}
      />
      {patients.isError && <Alert severity="error">{t("genericError")}</Alert>}
      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead><TableRow>
            <TableCell>{t("fullName")}</TableCell><TableCell>{t("birthDate")}</TableCell>
            <TableCell>{t("contact")}</TableCell><TableCell>{t("countryCode")}</TableCell>
            <TableCell>{t("status")}</TableCell><TableCell align="right">{t("actions")}</TableCell>
          </TableRow></TableHead>
          <TableBody>
            {patients.data?.results.map((patient) => (
              <TableRow key={patient.public_id} hover>
                <TableCell>{patient.first_name} {patient.last_name}</TableCell>
                <TableCell>{patient.birth_date}</TableCell>
                <TableCell>{patient.email || patient.phone || "—"}</TableCell>
                <TableCell>{patient.country_code || "—"}</TableCell>
                <TableCell><Chip size="small" color={patient.is_active ? "success" : "default"} label={patient.is_active ? t("active") : t("inactive")} /></TableCell>
                <TableCell align="right">
                  <IconButton aria-label={t("viewPatient")} onClick={() => setViewedPatient(patient)}><VisibilityOutlined /></IconButton>
                  {canEdit && <IconButton aria-label={t("editPatient")} onClick={() => openEdit(patient)}><EditOutlined /></IconButton>}
                </TableCell>
              </TableRow>
            ))}
            {!patients.isPending && patients.data?.results.length === 0 && (
              <TableRow><TableCell colSpan={6} align="center">{t("noPatients")}</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <Stack direction="row" justifyContent="flex-end" gap={1}>
        <Button disabled={!patients.data?.previous} onClick={() => setPage((value) => value - 1)}>{t("previous")}</Button>
        <Button disabled={!patients.data?.next} onClick={() => setPage((value) => value + 1)}>{t("next")}</Button>
      </Stack>
      <PatientDialog open={dialogOpen} patient={selectedPatient} canSeeClinicalFields={canSeeClinicalFields} onClose={() => setDialogOpen(false)} />
      <PatientDetailsDialog patient={viewedPatient} onClose={() => setViewedPatient(null)} />
    </Stack>
  );
}

