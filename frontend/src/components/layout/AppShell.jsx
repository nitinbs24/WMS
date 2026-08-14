import { Outlet, NavLink } from 'react-router-dom';
import { useAuthStore } from '../../store/useAuthStore';
import { useNavigate } from 'react-router-dom';

const NAV_ITEMS = [
  {
    section: 'Main',
    items: [
      { path: '/', label: 'Dashboard', icon: GridIcon, end: true },
      { path: '/twin', label: '3D Digital Twin', icon: CubeIcon },
      { path: '/runs', label: 'Run History', icon: ClockIcon },
      { path: '/runs/new', label: 'New Run', icon: PlayIcon },
    ],
  },
  {
    section: 'Admin',
    items: [
      { path: '/admin/settings', label: 'Threshold Settings', icon: SettingsIcon },
    ],
    adminOnly: true,
  },
];

export default function AppShell() {
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const navigate = useNavigate();

  const handleLogout = () => {
    clearAuth();
    navigate('/login');
  };

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <nav className="sidebar">
        <div className="sidebar-logo">
          <h1>Warehaven</h1>
          <span>Slotting Optimization</span>
        </div>

        <div style={{ flex: 1, overflow: 'auto' }}>
          {NAV_ITEMS.map((section) => {
            if (section.adminOnly && user?.role !== 'admin') return null;
            return (
              <div key={section.section} className="nav-section">
                <div className="nav-section-label">{section.section}</div>
                {section.items.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.end}
                    className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                  >
                    <item.icon className="nav-icon" />
                    {item.label}
                  </NavLink>
                ))}
              </div>
            );
          })}
        </div>

        {/* User footer */}
        <div style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--color-border-subtle)',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--color-primary), var(--color-accent))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 13, fontWeight: 700, color: '#fff', flexShrink: 0,
          }}>
            {user?.name?.[0]?.toUpperCase() || 'U'}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text)', truncate: 'ellipsis' }}>{user?.name}</div>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{user?.role}</div>
          </div>
          <button
            className="btn btn-ghost btn-sm"
            onClick={handleLogout}
            title="Sign out"
            style={{ padding: '4px 8px' }}
          >
            <LogoutIcon size={14} />
          </button>
        </div>
      </nav>

      {/* Main content area */}
      <main className="main-content">
        <div className="page-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

/* Inline icon components */
function GridIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="1" y="1" width="6" height="6" rx="1" /><rect x="9" y="1" width="6" height="6" rx="1" />
      <rect x="1" y="9" width="6" height="6" rx="1" /><rect x="9" y="9" width="6" height="6" rx="1" />
    </svg>
  );
}
function CubeIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M8 1 L14 4.5 L14 11.5 L8 15 L2 11.5 L2 4.5 Z" /><path d="M8 1 L8 15" /><path d="M2 4.5 L14 4.5" />
    </svg>
  );
}
function ClockIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="6.5" /><path d="M8 4.5 L8 8 L10.5 10" />
    </svg>
  );
}
function PlayIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="6.5" /><path d="M6.5 5.5 L11 8 L6.5 10.5 Z" fill="currentColor" stroke="none" />
    </svg>
  );
}
function SettingsIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="2" />
      <path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M12.6 3.4l-1.4 1.4M4.8 11.2l-1.4 1.4" />
    </svg>
  );
}
function LogoutIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M6 2H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3" /><path d="M10.5 5 L14 8 L10.5 11" /><line x1="6.5" y1="8" x2="14" y2="8" />
    </svg>
  );
}
