import { useEffect, useState } from "react";
import RepoList from "../components/RepoList.jsx";
import { fetchStatus } from "../api.js";

export default function AllReposPage() {
  const [pollSeconds, setPollSeconds] = useState(30);
  useEffect(() => {
    function loadStatus() {
      fetchStatus()
        .then((s) => {
          setPollSeconds(s.frontend_poll_seconds || 30);
        })
        .catch(() => {});
    }
    loadStatus();
    const id = setInterval(loadStatus, 60_000);
    return () => clearInterval(id);
  }, []);
  return (
    <RepoList
      mode="all"
      title="全部仓库"
      pollSeconds={pollSeconds}
      showSubscribe
    />
  );
}
