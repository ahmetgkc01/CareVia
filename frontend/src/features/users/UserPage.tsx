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
import { ManagedUser, ManagedUserInput, userApi } from "./api";

const roles = ["Admin", "Doctor", "Nurse", "Secretary", "Patient", "Auditor"] as const;
const userSchema = z.object({
  username: z.string().min(3),
  email: z.email(),
  first_name: z.string().min(1),
  last_name: z.string().min(1),
  role: z.enum(roles),
  password: z.string(),
  is_active: z.boolean(),
});
type UserForm = z.infer<typeof userSchema>;

const emptyUser: UserForm = {
  username: "",
  email: "",
  first_name: "",
  last_name: "",
  role: "Patient",
  password: "",
  is_active: true,
};

function UserDialog({ open, user, onClose }: { open: boolean; user: ManagedUser | null; onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const form = useForm<UserForm>({ resolver: zodResolver(userSchema), defaultValues: emptyUser });
  useEffect(() => {
    form.reset(
      user
        ? {
            username: user.username,
            email: user.email,
            first_name: user.first_name,
            last_name: user.last_name,
            role: (user.groups[0] as UserForm["role"]) ?? "Patient",
            password: "",
            is_active: user.is_active,
          }
        : emptyUser,
    );
  }, [form, open, user]);
  const mutation = useMutation({
    mutationFn: (values: UserForm) => {
      if (!user && values.password.length < 8) throw new Error("password-required");
      const payload: ManagedUserInput = {
        username: values.username,
        email: values.email,
        first_name: values.first_name,
        last_name: values.last_name,
        groups: [values.role],
        is_active: values.is_active,
        ...(values.password ? { password: values.password } : {}),
      };
      return user ? userApi.update(user.id, payload) : userApi.create(payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
  });
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <Box component="form" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <DialogTitle>{user ? t("editUser") : t("addUser")}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} pt={1}>
            <TextField label={t("username")} error={Boolean(form.formState.errors.username)} {...form.register("username")} />
            <TextField label={t("email")} type="email" error={Boolean(form.formState.errors.email)} {...form.register("email")} />
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <TextField fullWidth label={t("firstName")} {...form.register("first_name")} />
              <TextField fullWidth label={t("lastName")} {...form.register("last_name")} />
            </Stack>
            <TextField select label={t("role")} defaultValue="Patient" {...form.register("role")}>
              {roles.map((role) => <MenuItem key={role} value={role}>{role}</MenuItem>)}
            </TextField>
            <TextField
              label={user ? t("newPasswordOptional") : t("password")}
              type="password"
              error={Boolean(form.formState.errors.password)}
              helperText={!user ? t("minimumEightCharacters") : undefined}
              {...form.register("password")}
            />
            <TextField select label={t("status")} defaultValue="true" {...form.register("is_active", { setValueAs: (value) => value === "true" })}>
              <MenuItem value="true">{t("active")}</MenuItem>
              <MenuItem value="false">{t("inactive")}</MenuItem>
            </TextField>
            {mutation.isError && <Alert severity="error">{t("userSaveError")}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>{t("cancel")}</Button>
          <Button variant="contained" type="submit" disabled={mutation.isPending}>{t("save")}</Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
}

export function UserPage() {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<ManagedUser | null>(null);
  const session = useQuery({ queryKey: ["session"], queryFn: authApi.me });
  const users = useQuery({ queryKey: ["users", search, page], queryFn: () => userApi.list(search, page) });
  const canEdit = session.data?.groups.includes("Admin") ?? false;
  const openNew = () => { setSelectedUser(null); setDialogOpen(true); };
  const openEdit = (user: ManagedUser) => { setSelectedUser(user); setDialogOpen(true); };

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
        <Box><Typography variant="h4">{t("users")}</Typography><Typography color="text.secondary">{t("userManagementDescription")}</Typography></Box>
        {canEdit && <Button variant="contained" startIcon={<AddOutlined />} onClick={openNew}>{t("addUser")}</Button>}
      </Stack>
      <TextField value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder={t("searchUsers")} sx={{ maxWidth: 420 }} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchOutlined /></InputAdornment> } }} />
      {users.isError && <Alert severity="error">{t("userListForbidden")}</Alert>}
      <TableContainer component={Paper} variant="outlined"><Table>
        <TableHead><TableRow><TableCell>{t("fullName")}</TableCell><TableCell>{t("username")}</TableCell><TableCell>{t("email")}</TableCell><TableCell>{t("role")}</TableCell><TableCell>{t("status")}</TableCell>{canEdit && <TableCell align="right">{t("actions")}</TableCell>}</TableRow></TableHead>
        <TableBody>{users.data?.results.map((user) => <TableRow key={user.id} hover>
          <TableCell>{user.first_name} {user.last_name}</TableCell><TableCell>{user.username}</TableCell><TableCell>{user.email}</TableCell>
          <TableCell>{user.groups.join(", ") || "—"}</TableCell><TableCell><Chip size="small" color={user.is_active ? "success" : "default"} label={user.is_active ? t("active") : t("inactive")} /></TableCell>
          {canEdit && <TableCell align="right"><IconButton aria-label={t("editUser")} onClick={() => openEdit(user)}><EditOutlined /></IconButton></TableCell>}
        </TableRow>)}</TableBody>
      </Table></TableContainer>
      <Stack direction="row" justifyContent="flex-end" gap={1}><Button disabled={!users.data?.previous} onClick={() => setPage((value) => value - 1)}>{t("previous")}</Button><Button disabled={!users.data?.next} onClick={() => setPage((value) => value + 1)}>{t("next")}</Button></Stack>
      <UserDialog open={dialogOpen} user={selectedUser} onClose={() => setDialogOpen(false)} />
    </Stack>
  );
}

