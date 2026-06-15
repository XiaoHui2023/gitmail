import { NavLink, Outlet } from "react-router-dom";
import ThemeBar from "./ThemeBar.jsx";

export default function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <nav>
          <NavLink to="/" end>
            全部仓库
          </NavLink>
          <NavLink to="/subscriptions">我的订阅</NavLink>
          <NavLink to="/settings">设置</NavLink>
        </nav>
      </aside>
      <div className="app-body">
        <ThemeBar />
        <main className="page-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
