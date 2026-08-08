import { ArchitecturePage } from "@/pages/ArchitecturePage";
import { DataSourcesPage } from "@/pages/DataSourcesPage";
import { PowerBiPage } from "@/pages/PowerBiPage";
import { Workspace } from "@/pages/Workspace";
import { Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/copilot" replace />} />
        <Route path="/copilot" element={<Workspace />} />
        <Route path="/data-sources" element={<DataSourcesPage />} />
        <Route path="/connect" element={<Navigate to="/data-sources" replace />} />
        <Route path="/sql-agent" element={<Navigate to="/copilot" replace />} />
        <Route path="/power-bi" element={<PowerBiPage />} />
        <Route path="/architecture" element={<ArchitecturePage />} />
        <Route path="*" element={<Navigate to="/copilot" replace />} />
      </Routes>
      <Toaster theme="dark" position="top-right" richColors closeButton />
    </>
  );
}
