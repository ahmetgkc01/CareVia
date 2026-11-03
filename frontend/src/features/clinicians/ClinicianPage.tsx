import { zodResolver } from "@hookform/resolvers/zod";
import { AddOutlined, EditOutlined, SearchOutlined } from "@mui/icons-material";
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
import { Clinician, ClinicianInput, clinicianApi } from "./api";

const clinicianSchema = z.object({
  username: z.string().trim()
    .min(1, { message: "validationRequired" })
    .min(3, { message: "validationUsernameMin" }),
  first_name: z.string().trim().min(1, { message: "validationRequired" }),
  last_name: z.string().trim().min(1, { message: "validationRequired" }),
  email: z.string().trim()
    .min(1, { message: "validationRequired" })
    .pipe(z.email({ message: "validationEmail" })),
  password: z.string().refine((value) => value.length === 0 || value.length >= 8, {
    message: "validationPasswordMin",
  }),
  profession: z.enum(["doctor", "nurse"]),
  specialty: z.string().max(120),
  country_code: z.string().max(2),
  is_active: z.boolean(),
});
type ClinicianForm = z.infer<typeof clinicianSchema>;

const emptyClinician: ClinicianForm = {
  username: "",
  first_name: "",
  last_name: "",
  email: "",
  password: "",
  profession: "doctor",
  specialty: "",
  country_code: "",
  is_active: true,
};

function ClinicianDialog({
  open,
  clinician,
  onClose,
}: {
  open: boolean;
  clinician: Clinician | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const form = useForm<ClinicianForm>({
    resolver: zodResolver(clinicianSchema),
    defaultValues: emptyClinician,
  });
  const errorText = (message?: string) => (message ? t(message) : undefined);
  useEffect(() => {
    form.reset(clinician ? { ...clinician, password: "" } : emptyClinician);
  }, [clinician, form, open]);
  const mutation = useMutation({
    mutationFn: (values: ClinicianForm) => {
      const { password, ...profile } = values;
      const payload: ClinicianInput = {
        ...profile,
        ...(password ? { password } : {}),
      };
      return clinician
        ? clinicianApi.update(clinician.public_id, payload)
        : clinicianApi.create(payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["clinicians"] });
      await queryClient.invalidateQueries({ queryKey: ["clinician-options"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      onClose();
    },
  });

  const submit = (values: ClinicianForm) => {
    if (!clinician && !values.password) {
      form.setError("password", { message: "validationPasswordMin" }, { shouldFocus: true });
      return;
    }
    mutation.mutate(values);
  };

  const showCreatePasswordError = () => {
    if (!clinician && !form.getValues("password")) {
      form.setError("password", { message: "validationPasswordMin" }, { shouldFocus: false });
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <Box component="form" noValidate onSubmit={form.handleSubmit(submit, showCreatePasswordError)}>
        <DialogTitle>{clinician ? t("editClinician") : t("addClinician")}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} pt={1}>
            <Typography variant="caption" color="text.secondary">{t("requiredFieldsHint")}</Typography>
            <TextField required label={t("username")} error={Boolean(form.formState.errors.username)} helperText={errorText(form.formState.errors.username?.message)} {...form.register("username")} />
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <TextField required fullWidth label={t("firstName")} error={Boolean(form.formState.errors.first_name)} helperText={errorText(form.formState.errors.first_name?.message)} {...form.register("first_name")} />
              <TextField required fullWidth label={t("lastName")} error={Boolean(form.formState.errors.last_name)} helperText={errorText(form.formState.errors.last_name?.message)} {...form.register("last_name")} />
            </Stack>
            <TextField required label={t("email")} type="email" error={Boolean(form.formState.errors.email)} helperText={errorText(form.formState.errors.email?.message)} {...form.register("email")} />
            <TextField required select label={t("profession")} defaultValue="doctor" {...form.register("profession")}>
              <MenuItem value="doctor">{t("doctor")}</MenuItem>
              <MenuItem value="nurse">{t("nurse")}</MenuItem>
            </TextField>
            <TextField label={t("specialty")} {...form.register("specialty")} />
            <TextField label={t("countryCode")} inputProps={{ maxLength: 2 }} {...form.register("country_code")} />
            <TextField
              required={!clinician}
              label={clinician ? t("newPasswordOptional") : t("password")}
              type="password"
              error={Boolean(form.formState.errors.password)}
              helperText={errorText(form.formState.errors.password?.message) ?? (!clinician ? t("minimumEightCharacters") : undefined)}
              {...form.register("password")}
            />
            <TextField select label={t("status")} defaultValue="true" {...form.register("is_active", { setValueAs: (value) => value === "true" })}>
              <MenuItem value="true">{t("active")}</MenuItem>
              <MenuItem value="false">{t("inactive")}</MenuItem>
            </TextField>
            {mutation.isError && <Alert severity="error">{t("clinicianSaveError")}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>{t("cancel")}</Button>
          <Button type="submit" variant="contained" disabled={mutation.isPending}>{t("save")}</Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
}

export function ClinicianPage() {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selected, setSelected] = useState<Clinician | null>(null);
  const session = useQuery({ queryKey: ["session"], queryFn: authApi.me });
  const clinicians = useQuery({
    queryKey: ["clinicians", search],
    queryFn: () => clinicianApi.list(search),
  });
  const canEdit = session.data?.is_superuser || (session.data?.groups.includes("Admin") ?? false);

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
        <Box>
          <Typography variant="h4">{t("clinicians")}</Typography>
          <Typography color="text.secondary">{t("clinicianManagementDescription")}</Typography>
        </Box>
        {canEdit && <Button variant="contained" startIcon={<AddOutlined />} onClick={() => { setSelected(null); setDialogOpen(true); }}>{t("addClinician")}</Button>}
      </Stack>
      <TextField
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder={t("searchClinicians")}
        sx={{ maxWidth: 420 }}
        slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchOutlined /></InputAdornment> } }}
      />
      {clinicians.isError && <Alert severity="error">{t("genericError")}</Alert>}
      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead><TableRow><TableCell>{t("fullName")}</TableCell><TableCell>{t("profession")}</TableCell><TableCell>{t("specialty")}</TableCell><TableCell>{t("email")}</TableCell><TableCell>{t("status")}</TableCell>{canEdit && <TableCell align="right">{t("actions")}</TableCell>}</TableRow></TableHead>
          <TableBody>
            {clinicians.data?.results.map((clinician) => (
              <TableRow key={clinician.public_id} hover>
                <TableCell>{clinician.first_name} {clinician.last_name}</TableCell>
                <TableCell>{t(clinician.profession)}</TableCell>
                <TableCell>{clinician.specialty || "—"}</TableCell>
                <TableCell>{clinician.email}</TableCell>
                <TableCell><Chip size="small" color={clinician.is_active ? "success" : "default"} label={clinician.is_active ? t("active") : t("inactive")} /></TableCell>
                {canEdit && <TableCell align="right"><IconButton aria-label={t("editClinician")} onClick={() => { setSelected(clinician); setDialogOpen(true); }}><EditOutlined /></IconButton></TableCell>}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <ClinicianDialog open={dialogOpen} clinician={selected} onClose={() => setDialogOpen(false)} />
    </Stack>
  );
}
