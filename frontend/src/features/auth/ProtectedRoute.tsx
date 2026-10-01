import { Box, CircularProgress } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { authApi } from "./api";

export function ProtectedRoute() {
  const location = useLocation();
  const session = useQuery({ queryKey: ["session"], queryFn: authApi.me, retry: false });
  if (session.isPending) {
    return (
      <Box minHeight="100vh" display="grid" sx={{ placeItems: "center" }}>
        <CircularProgress />
      </Box>
    );
  }
  if (session.isError) return <Navigate to="/login" state={{ from: location }} replace />;
  return <Outlet />;
}

