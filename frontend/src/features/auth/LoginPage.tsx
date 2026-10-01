import { zodResolver } from "@hookform/resolvers/zod";
import { LockOutlined } from "@mui/icons-material";
import { Alert, Avatar, Box, Button, Card, CardContent, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { ApiError } from "../../shared/api/client";
import { authApi } from "./api";

const loginSchema = z.object({ username: z.string().min(1), password: z.string().min(1) });
type LoginForm = z.infer<typeof loginSchema>;

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const form = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });
  const mutation = useMutation({
    mutationFn: async (values: LoginForm) => {
      await authApi.csrf();
      return authApi.login(values);
    },
    onSuccess: (user) => {
      queryClient.setQueryData(["session"], user);
      const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
      navigate(destination ?? "/dashboard", { replace: true });
    },
  });
  return (
    <Box minHeight="100vh" display="grid" sx={{ placeItems: "center", p: 2 }}>
      <Card sx={{ width: "100%", maxWidth: 420 }}>
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={3} component="form" onSubmit={form.handleSubmit((data) => mutation.mutate(data))}>
            <Stack alignItems="center" spacing={1}>
              <Avatar sx={{ bgcolor: "primary.main" }}><LockOutlined /></Avatar>
              <Typography variant="h5" fontWeight={700}>{t("signIn")}</Typography>
              <Typography color="text.secondary">{t("appName")}</Typography>
            </Stack>
            {mutation.isError && (
              <Alert severity="error">
                {mutation.error instanceof ApiError
                  ? t(mutation.error.status === 429 ? "tooManyLoginAttempts" : "invalidCredentials")
                  : t("genericError")}
              </Alert>
            )}
            <TextField label={t("username")} autoComplete="username" error={Boolean(form.formState.errors.username)} {...form.register("username")} />
            <TextField label={t("password")} type="password" autoComplete="current-password" error={Boolean(form.formState.errors.password)} {...form.register("password")} />
            <Button type="submit" variant="contained" size="large" disabled={mutation.isPending}>
              {mutation.isPending ? <CircularProgress size={24} color="inherit" /> : t("signIn")}
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}

