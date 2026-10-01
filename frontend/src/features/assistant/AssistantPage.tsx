import {
  AutoAwesomeOutlined,
  DeleteOutline,
  SendOutlined,
} from "@mui/icons-material";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { authApi } from "../auth/api";
import { patientApi } from "../patients/api";
import { assistantApi } from "./api";

export function AssistantPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [message, setMessage] = useState("");
  const [patientId, setPatientId] = useState("");
  const session = useQuery({ queryKey: ["session"], queryFn: authApi.me });
  const groups = session.data?.groups ?? [];
  const isDoctor = groups.includes("Doctor") || groups.includes("Admin");
  const canUseAssistant = isDoctor || groups.includes("Patient");
  const history = useQuery({
    queryKey: ["assistant-history"],
    queryFn: assistantApi.history,
    enabled: canUseAssistant,
  });
  const patients = useQuery({
    queryKey: ["assistant-patients"],
    queryFn: () => patientApi.list("", 1, 100),
    enabled: isDoctor,
  });
  const sendMessage = useMutation({
    mutationFn: assistantApi.send,
    onSuccess: async () => {
      setMessage("");
      await queryClient.invalidateQueries({ queryKey: ["assistant-history"] });
    },
  });
  const clearHistory = useMutation({
    mutationFn: assistantApi.clear,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["assistant-history"] });
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history.data, sendMessage.isPending]);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || sendMessage.isPending) return;
    sendMessage.mutate({
      message: trimmed,
      language: i18n.resolvedLanguage === "en" ? "en" : "tr",
      ...(isDoctor && patientId ? { patient_id: patientId } : {}),
    });
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  const quickPrompts = isDoctor
    ? [t("assistantPromptAllergies"), t("assistantPromptAppointments"), t("assistantPromptNotes")]
    : [t("assistantPromptMyAllergies"), t("assistantPromptMyAppointments"), t("assistantPromptProfile")];

  if (!canUseAssistant && session.isSuccess) {
    return <Alert severity="warning">{t("assistantRoleRestricted")}</Alert>;
  }

  return (
    <Stack spacing={2} sx={{ height: { xs: "auto", md: "calc(100vh - 128px)" } }}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
        <Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <AutoAwesomeOutlined color="primary" />
            <Typography variant="h4">{t("assistantTitle")}</Typography>
          </Stack>
          <Typography color="text.secondary">{t("assistantDescription")}</Typography>
        </Box>
        <Button
          color="inherit"
          startIcon={<DeleteOutline />}
          disabled={!history.data?.length || clearHistory.isPending}
          onClick={() => clearHistory.mutate()}
        >
          {t("clearChat")}
        </Button>
      </Stack>

      <Alert severity="warning">{t("assistantSafetyNotice")}</Alert>

      {isDoctor && (
        <TextField
          select
          size="small"
          label={t("assistantPatientContext")}
          value={patientId}
          onChange={(event) => setPatientId(event.target.value)}
          sx={{ maxWidth: 420 }}
        >
          <MenuItem value="">{t("assistantNoPatientSelected")}</MenuItem>
          {patients.data?.results.map((patient) => (
            <MenuItem key={patient.public_id} value={patient.public_id}>
              {patient.first_name} {patient.last_name}
            </MenuItem>
          ))}
        </TextField>
      )}

      <Paper
        variant="outlined"
        sx={{ display: "flex", flex: 1, minHeight: 420, flexDirection: "column", overflow: "hidden" }}
      >
        <Box sx={{ flex: 1, overflowY: "auto", p: { xs: 2, md: 3 } }}>
          {history.isLoading && (
            <Box display="flex" justifyContent="center" py={8}><CircularProgress /></Box>
          )}
          {history.isError && <Alert severity="error">{t("assistantLoadError")}</Alert>}
          {history.data?.length === 0 && (
            <Stack spacing={2} alignItems="center" textAlign="center" py={6}>
              <Avatar sx={{ bgcolor: "primary.main", width: 52, height: 52 }}>
                <AutoAwesomeOutlined />
              </Avatar>
              <Box>
                <Typography variant="h6">{t("assistantWelcome")}</Typography>
                <Typography color="text.secondary">{t("assistantWelcomeHint")}</Typography>
              </Box>
              <Stack direction="row" useFlexGap flexWrap="wrap" justifyContent="center" gap={1}>
                {quickPrompts.map((prompt) => (
                  <Chip key={prompt} label={prompt} onClick={() => setMessage(prompt)} clickable />
                ))}
              </Stack>
            </Stack>
          )}
          <Stack spacing={2}>
            {history.data?.map((item) => {
              const isUser = item.role === "user";
              const isSafety = Boolean(item.safety_code);
              return (
                <Box key={item.id} display="flex" justifyContent={isUser ? "flex-end" : "flex-start"}>
                  <Box
                    sx={{
                      maxWidth: { xs: "92%", md: "72%" },
                      bgcolor: isUser ? "primary.main" : isSafety ? "warning.50" : "grey.100",
                      color: isUser ? "primary.contrastText" : "text.primary",
                      border: isSafety ? 1 : 0,
                      borderColor: "warning.main",
                      borderRadius: 3,
                      px: 2,
                      py: 1.5,
                    }}
                  >
                    <Typography sx={{ whiteSpace: "pre-wrap" }}>{item.content}</Typography>
                    {item.sources.length > 0 && (
                      <Stack spacing={0.5} mt={1.5} pt={1} borderTop={1} borderColor="divider">
                        {item.sources.map((source, index) => (
                          <Typography key={`${source.label}-${index}`} variant="caption" color="text.secondary">
                            {t("source")}: {source.label}
                            {source.updated_at
                              ? ` · ${new Date(source.updated_at).toLocaleString(i18n.resolvedLanguage)}`
                              : ""}
                          </Typography>
                        ))}
                      </Stack>
                    )}
                  </Box>
                </Box>
              );
            })}
            {sendMessage.isPending && (
              <Box display="flex" justifyContent="flex-start">
                <Chip icon={<CircularProgress size={16} />} label={t("assistantThinking")} />
              </Box>
            )}
            <div ref={bottomRef} />
          </Stack>
        </Box>
        <Divider />
        <Box component="form" onSubmit={submit} p={2}>
          {sendMessage.isError && <Alert severity="error" sx={{ mb: 1 }}>{t("assistantSendError")}</Alert>}
          <Stack direction="row" spacing={1} alignItems="flex-end">
            <TextField
              fullWidth
              multiline
              maxRows={4}
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("assistantPlaceholder")}
              inputProps={{ maxLength: 2000 }}
            />
            <Button
              type="submit"
              variant="contained"
              aria-label={t("send")}
              disabled={!message.trim() || sendMessage.isPending}
              sx={{ minWidth: 52, height: 56 }}
            >
              <SendOutlined />
            </Button>
          </Stack>
          <Typography variant="caption" color="text.secondary">{t("assistantFooter")}</Typography>
        </Box>
      </Paper>
    </Stack>
  );
}
