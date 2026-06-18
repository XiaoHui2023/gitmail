import { useLayoutEffect, useRef } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import ThemeBar from "./ThemeBar.jsx";

export default function Layout() {
  const location = useLocation();
  const mainRef = useRef(null);
  const activePathRef = useRef(location.pathname);
  const scrollPositionsRef = useRef(new Map());

  useLayoutEffect(() => {
    const main = mainRef.current;
    if (!main) return;

    activePathRef.current = location.pathname;
    const savedTop = scrollPositionsRef.current.get(location.pathname) ?? 0;
    requestAnimationFrame(() => {
      main.scrollTop = savedTop;
    });
  }, [location.pathname]);

  function rememberScroll(event) {
    scrollPositionsRef.current.set(
      activePathRef.current,
      event.currentTarget.scrollTop,
    );
  }

  return (
    <div className="app-shell">
      <ThemeBar />
      <div className="app-main">
        <aside className="sidebar">
          <nav>
            <NavLink to="/" end>
              全部仓库
            </NavLink>
            <NavLink to="/subscriptions">我的订阅</NavLink>
            <NavLink to="/settings">设置</NavLink>
          </nav>
        </aside>
        <main className="page-main" ref={mainRef} onScroll={rememberScroll}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
