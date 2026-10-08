import {
  AutoAwesomeOutlined,
  DeleteOutline,
  SendOutlined,
} from "@mui/icons-material";
import {
  Alert,
  Autocomplete,
  Avatar,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
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
  const patientSelectRef = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState("");
  const [patientId, setPatientId] = useState("");
  const [patientSearch, setPatientSearch] = useState("");
  const [debouncedPatientSearch, setDebouncedPatientSearch] = useState("");
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);
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
    queryKey: ["assistant-patients", debouncedPatientSearch],
    queryFn: () => patientApi.list(debouncedPatientSearch, 1),
    enabled: isDoctor,
  });
  const sendMessage = useMutation({
    mutationFn: assistantApi.send,
    onSuccess: async (reply, input) => {
      setMessage("");
      if (isDoctor && reply.safety_code === "patient_context_required") {
        setPendingPrompt(input.message);
        patientSelectRef.current?.focus();
      }
      await queryClient.invalidateQueries({ queryKey: ["assistant-history"] });
    },
    onError: (_error, input) => setMessage(input.message),
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

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedPatientSearch(patientSearch.trim()), 300);
    return () => window.clearTimeout(timeout);
  }, [patientSearch]);

  const sendPrompt = (content: string, contextPatientId = patientId) => {
    sendMessage.mutate({
      message: content,
      language: i18n.resolvedLanguage === "en" ? "en" : "tr",
      ...(isDoctor && contextPatientId ? { patient_id: contextPatientId } : {}),
    });
  };

  const queueOrSendPrompt = (prompt: string, requiresPatient = true) => {
    if (requiresPatient && isDoctor && !patientId) {
      setPendingPrompt(prompt);
      setMessage("");
      patientSelectRef.current?.focus();
      return;
    }
    setPendingPrompt(null);
    sendPrompt(prompt);
  };

  const selectPatient = (selectedPatientId: string) => {
    setPatientId(selectedPatientId);
    if (selectedPatientId && pendingPrompt && !sendMessage.isPending) {
      const prompt = pendingPrompt;
      setPendingPrompt(null);
      sendPrompt(prompt, selectedPatientId);
    }
  };

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || sendMessage.isPending) return;
    sendPrompt(trimmed);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  const quickPrompts = isDoctor
    ? [
        { label: t("assistantPromptAllergyPatients"), requiresPatient: false },
        { label: t("assistantPromptAllergies"), requiresPatient: true },
        { label: t("assistantPromptAppointments"), requiresPatient: true },
        { label: t("assistantPromptNotes"), requiresPatient: true },
      ]
    : [
        { label: t("assistantPromptMyAllergies"), requiresPatient: false },
        { label: t("assistantPromptMyAppointments"), requiresPatient: false },
        { label: t("assistantPromptProfile"), requiresPatient: false },
      ];

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
        <Autocomplete
          size="small"
          options={patients.data?.results ?? []}
          loading={patients.isPending}
          filterOptions={(options) => options}
          getOptionLabel={(patient) => `${patient.first_name} ${patient.last_name}`}
          isOptionEqualToValue={(option, value) => option.public_id === value.public_id}
          value={patients.data?.results.find((patient) => patient.public_id === patientId) ?? null}
          inputValue={patientSearch}
          onInputChange={(_event, value, reason) => {
            if (reason !== "reset") setPatientSearch(value);
          }}
          onChange={(_event, patient) => {
            setPatientSearch(patient ? `${patient.first_name} ${patient.last_name}` : "");
            selectPatient(patient?.public_id ?? "");
          }}
          noOptionsText={t("noPatients")}
          sx={{ maxWidth: 420 }}
          renderInput={(params) => (
            <TextField
              {...params}
              label={t("assistantPatientContext")}
              placeholder={t("assistantPatientSearch")}
              inputRef={patientSelectRef}
            />
          )}
        />
      )}

      {isDoctor && pendingPrompt && (
        <Alert severity="info">
          {t("assistantPendingPatientPrompt", { prompt: pendingPrompt })}
        </Alert>
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
                  <Chip
                    key={prompt.label}
                    label={prompt.label}
                    onClick={() => queueOrSendPrompt(prompt.label, prompt.requiresPatient)}
                    disabled={sendMessage.isPending}
                    clickable
                  />
                ))}
              </Stack>
            </Stack>
          )}
          <Stack spacing={2}>
            {history.data?.map((item, itemIndex) => {
              const isUser = item.role === "user";
              const isSafety = Boolean(item.safety_code);
              const previousMessage = history.data[itemIndex - 1];
              const retryPrompt = item.safety_code === "patient_context_required"
                && previousMessage?.role === "user"
                ? previousMessage.content
                : null;
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
                    {retryPrompt && (
                      <Button
                        size="small"
                        variant="outlined"
                        disabled={sendMessage.isPending}
                        onClick={() => queueOrSendPrompt(retryPrompt)}
                        sx={{ mt: 1.5 }}
                      >
                        {t("assistantRetryPatientPrompt")}
                      </Button>
                    )}
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
