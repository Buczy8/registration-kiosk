import { Link } from "react-router-dom";

const NAV = [
  { href: "/admin/users", label: "Użytkownicy" },
  { href: "/admin/submissions", label: "Zgłoszenia" },
  { href: "/admin/print-jobs", label: "Wydruki" },
];

export default function AdminLayout({ title, subtitle, activeHref, children }) {
  return (
    <div className="admin-screen">
      <div className="form-header admin-header">
        <p className="eyebrow">Panel administracyjny</p>
        <h1>{title}</h1>
        {subtitle ? <p className="hint">{subtitle}</p> : null}

        <div className="admin-nav">
          {NAV.map((item) => {
            const isActive = activeHref === item.href;
            return (
              <Link
                key={item.href}
                className={isActive ? "admin-tab admin-tab--active" : "admin-tab"}
                to={item.href}
                aria-current={isActive ? "page" : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      </div>

      {children}
    </div>
  );
}
