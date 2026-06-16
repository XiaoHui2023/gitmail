import { useEffect, useState } from "react";
import RepoList from "../components/RepoList.jsx";
import { fetchStatus } from "../api.js";

export default function SubscriptionsPage() {
  const [pollSeconds, setPollSeconds] = useState(30);
  useEffect(() => {
    fetchStatus()
      .then((s) => setPollSeconds(s.frontend_poll_seconds || 30))
      .catch(() => {});
  }, []);
  return (
    <RepoList
      mode="subscribed"
      title="我的订阅"
      pollSeconds={pollSeconds}
      showSubscribe={false}
    />
  );
}
