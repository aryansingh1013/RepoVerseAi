import { HashRouter, Routes, Route } from "react-router-dom";
import { NavigationProvider } from "@/hooks/useNavigation";
import { LandingPage } from "@/pages/LandingPage";
import { IndexingScreen } from "@/pages/IndexingScreen";
import { WorkspacePage } from "@/pages/WorkspacePage";

export default function App() {
  return (
    <HashRouter>
      <NavigationProvider>
        <Routes>
          {/* Landing: choose workspace or git repo */}
          <Route path="/" element={<LandingPage />} />
          {/* Indexing progress: shown while backend indexes */}
          <Route path="/indexing" element={<IndexingScreen />} />
          {/* Galaxy workspace: the main 3D view */}
          <Route path="/workspace" element={<WorkspacePage />} />
        </Routes>
      </NavigationProvider>
    </HashRouter>
  );
}
