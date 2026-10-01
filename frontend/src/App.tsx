import { HashRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { NavigationProvider } from "@/hooks/useNavigation";
import { ChatProvider } from "@/hooks/useChat";
import { AuthProvider, useAuth } from "@/hooks/useAuth";
import { LandingPage } from "@/pages/LandingPage";
import { IndexingScreen } from "@/pages/IndexingScreen";
import { WorkspacePage } from "@/pages/WorkspacePage";
import AuthPage from "@/pages/AuthPage";
import { Loader2 } from "lucide-react";

function RequireAuth({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#030308]">
        <Loader2 className="w-8 h-8 text-violet-500 animate-spin" />
      </div>
    );
  }

  if (!user) {
    // Redirect to login, remembering where they were headed.
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

export default function App() {
  return (
    <HashRouter>
      <AuthProvider>
        <ChatProvider>
        <NavigationProvider>
          <Routes>
            {/* Auth */}
            <Route path="/login" element={<AuthPage />} />

            {/* Protected app routes */}
            <Route
              path="/"
              element={
                <RequireAuth>
                  <LandingPage />
                </RequireAuth>
              }
            />
            <Route
              path="/indexing"
              element={
                <RequireAuth>
                  <IndexingScreen />
                </RequireAuth>
              }
            />
            <Route
              path="/workspace"
              element={
                <RequireAuth>
                  <WorkspacePage />
                </RequireAuth>
              }
            />
          </Routes>
        </NavigationProvider>
        </ChatProvider>
      </AuthProvider>
    </HashRouter>
  );
}
