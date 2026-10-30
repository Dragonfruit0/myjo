/*
 * App shell + routes. Signed-out users see the sign-in page (or first-login setup); signed-in users get
 * the header (logo, global search, name, My account, Sign out), the side menu built from `screens`
 * (scrolling tab row on phones) and the routed screen.
 */
import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from './auth';
import { MetaProvider, useMetaState } from './meta';
import { get } from './api';
import { homePath, NAV, SCREEN_PATH } from './nav';
import type { ScreenCode } from './types';
import { ErrorBox, Loading } from './ui/Async';
import { ModalProvider } from './ui/Modal';
import { useMyAccount } from './pages/MyAccount';
import Login from './pages/Login';
import Setup from './pages/Setup';
import Dashboard from './pages/Dashboard';
import Requests from './pages/Requests';
import RequestDetailPage from './pages/RequestDetail';
import Marketing from './pages/Marketing';
import Orders from './pages/Orders';
import MyOrdersPage from './pages/MyOrders';
import OrderedSchools from './pages/OrderedSchools';
import Training from './pages/Training';
import TrainingDetailPage from './pages/TrainingDetail';
import Papers from './pages/Papers';
import Resources from './pages/Resources';
import DownloadsPage from './pages/Downloads';
import Reports from './pages/Reports';
import Notifications from './pages/Notifications';
import Audit from './pages/Audit';
import Users from './pages/Users';
import MastersPage from './pages/Masters';
import Access from './pages/Access';
import Search from './pages/Search';
import PortalOverview from './pages/portal/Overview';
import PortalTraining from './pages/portal/MyTraining';
import Library from './pages/portal/Library';
import Support from './pages/portal/Support';
import History from './pages/portal/History';

function Brand({ to }: { to: string }) {
  return (
    <Link className="brand" to={to} aria-label="Myjo portal home">
      <img src="/logo.png" alt="Myjo" />
      <span className="bsub">School Demo, Order &amp; Academic Support Portal</span>
    </Link>
  );
}

function SignedOutLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="top">
        <div className="top-in">
          <Brand to="/" />
        </div>
      </header>
      <div className="shell out">
        <main id="main">{children}</main>
      </div>
    </>
  );
}

function GlobalSearch() {
  const navigate = useNavigate();
  const location = useLocation();
  const [q, setQ] = useState(() => new URLSearchParams(location.search).get('q') ?? '');
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const t = q.trim();
    if (t) navigate('/search?q=' + encodeURIComponent(t));
  };
  return (
    <form className="gsearch" role="search" onSubmit={submit}>
      <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search school, distributor, city, mobile, DR no., PO, series, resource" aria-label="Global search" />
      <button type="submit">Search</button>
    </form>
  );
}

/** Numbers beside menu items (GET /nav-counts): things waiting for this user; refreshed on every page change. */
function useNavCounts(enabled: boolean): Partial<Record<ScreenCode, number>> {
  const { pathname } = useLocation();
  const [counts, setCounts] = useState<Partial<Record<ScreenCode, number>>>({});
  useEffect(() => {
    if (!enabled) return;
    let live = true;
    get<{ counts: Partial<Record<ScreenCode, number>> }>('/nav-counts')
      .then((r) => live && setCounts(r.counts ?? {}))
      .catch(() => {
        /* badges are a convenience; never block the page */
      });
    return () => {
      live = false;
    };
  }, [pathname, enabled]);
  return counts;
}

function SideNav({ screens }: { screens: ScreenCode[] }) {
  const { user } = useAuth();
  const counts = useNavCounts(!!user && user.role !== 'school');
  return (
    <nav className="side" aria-label="Sections">
      {NAV.map((g) => {
        const items = g.items.filter(([k]) => screens.includes(k));
        if (!items.length) return null;
        return (
          <div className="g" key={g.group}>
            <div className="gl">{g.group}</div>
            {items.map(([k, label]) => (
              <NavLink key={k} to={SCREEN_PATH[k]} end={k === 'portal' || k === 'dashboard'} className={({ isActive }) => 'nav' + (isActive ? ' on' : '')}>
                <span>{label}</span>
                {counts[k] ? (
                  <span className="ct" aria-label={`${counts[k]} waiting`}>
                    {counts[k]}
                  </span>
                ) : null}
              </NavLink>
            ))}
          </div>
        );
      })}
      {user && (
        <div className="role-card">
          <b>{user.name}</b>
          {user.role_label}
          {user.org && user.org !== user.name && (
            <>
              <br />
              {user.org}
            </>
          )}
          {user.school_name && (
            <>
              <br />
              {user.school_name}
            </>
          )}
        </div>
      )}
    </nav>
  );
}

function Guard({ screen, children }: { screen: ScreenCode | ScreenCode[]; children: ReactNode }) {
  const { sees, user, screens } = useAuth();
  const ok = ([] as ScreenCode[]).concat(screen).some(sees);
  if (!ok) return <Navigate to={homePath(user?.role ?? 'admin', screens)} replace />;
  return <>{children}</>;
}

function ScrollTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return null;
}

function SignedIn() {
  const { user, screens, logout } = useAuth();
  const { meta, error, reload } = useMetaState();
  const openAccount = useMyAccount();
  if (!user) return null;
  const home = homePath(user.role, screens);
  const internal: ScreenCode[] = ['requests', 'marketing', 'orders', 'myorders', 'acschools', 'dashboard'];

  return (
    <>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="top">
        <div className="top-in">
          <Brand to={home} />
          {user.role !== 'school' && <GlobalSearch />}
          <div className="who">
            <span className="who-n">
              <b>{user.name}</b>
              <span>
                {user.role_label}
                {user.school_name ? ' · ' + user.school_name.split(',')[0] : ''}
              </span>
            </span>
            <button type="button" className="btn sm" onClick={openAccount}>
              My account
            </button>
            <button type="button" className="btn sm" onClick={() => void logout()}>
              Sign out
            </button>
          </div>
        </div>
      </header>
      <div className="shell">
        <SideNav screens={screens} />
        <main id="main" tabIndex={-1}>
          {error && !meta ? (
            <ErrorBox message={'Could not load portal settings. ' + error.message} onRetry={reload} />
          ) : !meta ? (
            <Loading />
          ) : (
            <Routes>
              <Route path="/" element={<Navigate to={home} replace />} />
              <Route path="/login" element={<Navigate to={home} replace />} />
              <Route path="/dashboard" element={<Guard screen="dashboard"><Dashboard /></Guard>} />
              <Route path="/requests" element={<Guard screen="requests"><Requests /></Guard>} />
              <Route path="/requests/:id" element={<Guard screen={internal}><RequestDetailPage /></Guard>} />
              <Route path="/marketing" element={<Guard screen="marketing"><Marketing /></Guard>} />
              <Route path="/orders" element={<Guard screen="orders"><Orders /></Guard>} />
              <Route path="/my-orders" element={<Guard screen="myorders"><MyOrdersPage /></Guard>} />
              <Route path="/ordered-schools" element={<Guard screen="acschools"><OrderedSchools /></Guard>} />
              <Route path="/training" element={<Guard screen="training"><Training /></Guard>} />
              <Route path="/training/:id" element={<Guard screen="training"><TrainingDetailPage /></Guard>} />
              <Route path="/papers" element={<Guard screen="papers"><Papers /></Guard>} />
              <Route path="/resources" element={<Guard screen="resources"><Resources /></Guard>} />
              <Route path="/downloads" element={<Guard screen="downloads"><DownloadsPage /></Guard>} />
              <Route path="/reports" element={<Guard screen="reports"><Reports /></Guard>} />
              <Route path="/notifications" element={<Guard screen="notifications"><Notifications /></Guard>} />
              <Route path="/audit" element={<Guard screen="audit"><Audit /></Guard>} />
              <Route path="/users" element={<Guard screen="users"><Users /></Guard>} />
              <Route path="/masters" element={<Guard screen="masters"><MastersPage /></Guard>} />
              <Route path="/access" element={<Guard screen="access"><Access /></Guard>} />
              <Route path="/search" element={<Guard screen={internal}><Search /></Guard>} />
              <Route path="/portal" element={<Guard screen="portal"><PortalOverview /></Guard>} />
              <Route path="/portal/training" element={<Guard screen="mytraining"><PortalTraining /></Guard>} />
              <Route path="/portal/library" element={<Guard screen="library"><Library /></Guard>} />
              <Route path="/portal/support" element={<Guard screen="support"><Support /></Guard>} />
              <Route path="/portal/history" element={<Guard screen="history"><History /></Guard>} />
              <Route path="*" element={<Navigate to={home} replace />} />
            </Routes>
          )}
        </main>
      </div>
    </>
  );
}

export default function App() {
  const { status } = useAuth();
  return (
    <MetaProvider enabled={status === 'in'}>
      <ModalProvider>
        <ScrollTop />
        {status === 'loading' ? (
          <SignedOutLayout>
            <Loading label="Signing you in…" />
          </SignedOutLayout>
        ) : status === 'out' ? (
          <SignedOutLayout>
            <Login />
          </SignedOutLayout>
        ) : status === 'setup' ? (
          <SignedOutLayout>
            <Setup />
          </SignedOutLayout>
        ) : (
          <SignedIn />
        )}
      </ModalProvider>
    </MetaProvider>
  );
}
