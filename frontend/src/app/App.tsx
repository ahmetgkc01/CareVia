import {
  AutoAwesomeOutlined,
  CalendarMonthOutlined,
  CheckCircleOutline,
  MedicalServicesOutlined,
  DashboardOutlined,
  GroupsOutlined,
  LanguageOutlined,
  LogoutOutlined,
  MenuOutlined,
  OpenInNewOutlined,
  PeopleAltOutlined,
} from "@mui/icons-material";
import {
  Alert,
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  Paper,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, Outlet, Route, Routes, useNavigate } from "react-router-dom";

import { authApi } from "../features/auth/api";
import { ProtectedRoute } from "../features/auth/ProtectedRoute";
import { dashboardApi } from "../features/dashboard/api";

const AssistantPage = lazy(() =>
  import("../features/assistant/AssistantPage").then((module) => ({ default: module.AssistantPage })),
);
const LoginPage = lazy(() =>
  import("../features/auth/LoginPage").then((module) => ({ default: module.LoginPage })),
);
const AppointmentPage = lazy(() =>
  import("../features/appointments/AppointmentPage").then((module) => ({ default: module.AppointmentPage })),
);
const ClinicianPage = lazy(() =>
  import("../features/clinicians/ClinicianPage").then((module) => ({ default: module.ClinicianPage })),
);
const PatientPage = lazy(() =>
  import("../features/patients/PatientPage").then((module) => ({ default: module.PatientPage })),
);
const UserPage = lazy(() =>
  import("../features/users/UserPage").then((module) => ({ default: module.UserPage })),
);

const drawerWidth = 240;

function PageLoader() {
  return (
    <Box minHeight="50vh" display="grid" sx={{ placeItems: "center" }}>
      <CircularProgress />
    </Box>
  );
}

function DashboardPage() {
  const { t, i18n } = useTranslation();
  const summary = useQuery({ queryKey: ["dashboard-summary"], queryFn: dashboardApi.summary });
  const release = useQuery({ queryKey: ["release-overview"], queryFn: dashboardApi.release });
  const patientScope = summary.data?.scope === "patient";
  const metrics = [
    [patientScope ? t("myPatientProfile") : t("totalPatients"), summary.data?.total_patients],
    [patientScope ? t("myUpcomingAppointments") : t("upcomingAppointments"), summary.data?.upcoming_appointments],
    [t("activeDoctors"), summary.data?.active_doctors],
    [t("activeNurses"), summary.data?.active_nurses],
  ];
  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4">{t("dashboard")}</Typography>
        <Typography color="text.secondary">{t("welcome")}</Typography>
      </Box>
      <Alert severity="info">{t("demoNotice")}</Alert>
      {summary.isError && <Alert severity="error">{t("dashboardLoadError")}</Alert>}
      <Box display="grid" gridTemplateColumns={{ xs: "1fr", md: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" }} gap={2}>
        {metrics.map(([label, value]) => (
          <Card key={label} variant="outlined">
            <CardContent>
              <Typography color="text.secondary">{label}</Typography>
              <Typography variant="h4">{value ?? "—"}</Typography>
            </CardContent>
          </Card>
        ))}
      </Box>
      <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}>
        <Stack spacing={2.5}>
          <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={2}>
            <Box>
              <Typography variant="h6">{t("developmentHistory")}</Typography>
              <Typography color="text.secondary">{t("developmentHistoryDescription")}</Typography>
            </Box>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
              <Chip
                color="primary"
                label={`${t("currentRelease")}: ${release.data?.release ?? "—"}`}
              />
              {release.data && (
                <Button
                  size="small"
                  endIcon={<OpenInNewOutlined />}
                  href={release.data.changelog_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("viewChangelog")}
                </Button>
              )}
            </Stack>
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            {[t("qualityChecks"), t("changelogStep"), t("commitStep"), t("githubPushStep")].map((step, index) => (
              <Stack direction="row" spacing={1} alignItems="center" key={step}>
                <Chip size="small" icon={<CheckCircleOutline />} label={step} variant="outlined" />
                {index < 3 && <Typography color="text.disabled">→</Typography>}
              </Stack>
            ))}
          </Stack>
          <Divider />
          {release.isError && <Alert severity="warning">{t("releaseHistoryError")}</Alert>}
          <Stack spacing={1.5}>
            {release.data?.commits.map((commit) => (
              <Stack
                key={commit.sha}
                direction={{ xs: "column", sm: "row" }}
                spacing={1.5}
                alignItems={{ sm: "center" }}
              >
                <Chip
                  size="small"
                  label={commit.sha.slice(0, 7)}
                  component="a"
                  clickable
                  href={`${release.data.repository_url}/commit/${commit.sha}`}
                  target="_blank"
                  rel="noreferrer"
                  sx={{ fontFamily: "monospace" }}
                />
                <Box flexGrow={1}>
                  <Typography fontWeight={600}>{commit.message}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {new Intl.DateTimeFormat(i18n.resolvedLanguage, {
                      dateStyle: "medium",
                      timeStyle: "short",
                    }).format(new Date(commit.committed_at))}
                  </Typography>
                </Box>
              </Stack>
            ))}
            {release.data && release.data.commits.length === 0 && (
              <Typography color="text.secondary">{t("releaseHistoryUnavailable")}</Typography>
            )}
          </Stack>
        </Stack>
      </Paper>
    </Stack>
  );
}

function AppShell() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const session = useQuery({ queryKey: ["session"], queryFn: authApi.me });
  const health = useQuery({
    queryKey: ["health"],
    queryFn: dashboardApi.health,
    retry: false,
    staleTime: Infinity,
  });
  const canViewUsers = session.data?.groups.some((group) => ["Admin", "Auditor"].includes(group));
  const canUseAssistant = session.data?.groups.some((group) => ["Doctor", "Patient"].includes(group)) || session.data?.groups.includes("Admin");
  const release = health.data?.release;
  const displayedRelease = release && release.length > 12 ? release.slice(0, 7) : release;
  const items = [
    [t("dashboard"), "/dashboard", <DashboardOutlined />],
    [t("patients"), "/patients", <PeopleAltOutlined />],
    [t("clinicians"), "/clinicians", <MedicalServicesOutlined />],
    [t("appointments"), "/appointments", <CalendarMonthOutlined />],
    ...(canUseAssistant ? [[t("assistant"), "/assistant", <AutoAwesomeOutlined />] as const] : []),
    ...(canViewUsers ? [[t("users"), "/users", <GroupsOutlined />] as const] : []),
  ] as const;

  const changeLanguage = () => {
    const nextLanguage = i18n.resolvedLanguage === "tr" ? "en" : "tr";
    void i18n.changeLanguage(nextLanguage);
    document.documentElement.lang = nextLanguage;
  };
  const signOut = async () => {
    await authApi.logout();
    queryClient.removeQueries({ queryKey: ["session"] });
    navigate("/login", { replace: true });
  };
  const navigation = (
    <>
      <Toolbar />
      <List>
        {items.map(([label, path, icon]) => (
          <ListItemButton
            key={path}
            component={Link}
            to={path}
            onClick={() => setMobileMenuOpen(false)}
          >
            <ListItemIcon>{icon}</ListItemIcon>
            <ListItemText primary={label} />
          </ListItemButton>
        ))}
      </List>
    </>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar position="fixed" sx={{ zIndex: (muiTheme) => muiTheme.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            aria-label={t("openMenu")}
            onClick={() => setMobileMenuOpen(true)}
            sx={{ mr: 1, display: { md: "none" } }}
          >
            <MenuOutlined />
          </IconButton>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>{t("appName")}</Typography>
          <Button color="inherit" startIcon={<LanguageOutlined />} onClick={changeLanguage}>
            {i18n.resolvedLanguage === "tr" ? "EN" : "TR"}
          </Button>
          <Button color="inherit" startIcon={<LogoutOutlined />} onClick={() => void signOut()}>
            {t("signOut")}
          </Button>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: { md: drawerWidth },
          display: { xs: "none", md: "block" },
          [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: "border-box" },
        }}
      >
        {navigation}
      </Drawer>
      <Drawer
        variant="temporary"
        open={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: "block", md: "none" },
          [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: "border-box" },
        }}
      >
        {navigation}
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, py: 4 }}>
        <Toolbar />
        <Container maxWidth="xl"><Outlet /></Container>
      </Box>
      <Box
        title={release}
        sx={{ position: "fixed", right: 12, bottom: 10, zIndex: (muiTheme) => muiTheme.zIndex.drawer + 1 }}
      >
        <Chip
          size="small"
          variant="outlined"
          label={`${t("version")}: ${displayedRelease ?? "—"}`}
          sx={{ bgcolor: "background.paper", color: "text.secondary" }}
        />
      </Box>
    </Box>
  );
}

export function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/patients" element={<PatientPage />} />
            <Route path="/clinicians" element={<ClinicianPage />} />
            <Route path="/appointments" element={<AppointmentPage />} />
            <Route path="/assistant" element={<AssistantPage />} />
            <Route path="/users" element={<UserPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}

