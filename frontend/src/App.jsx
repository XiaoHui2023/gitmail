import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import AllReposPage from "./pages/AllRepos.jsx";
import SubscriptionsPage from "./pages/Subscriptions.jsx";
import SettingsPage from "./pages/Settings.jsx";
import WebhooksPage from "./pages/Webhooks.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<AllReposPage />} />
        <Route path="subscriptions" element={<SubscriptionsPage />} />
        <Route path="webhooks" element={<WebhooksPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
