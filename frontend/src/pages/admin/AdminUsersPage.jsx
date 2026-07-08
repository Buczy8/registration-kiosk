import { useEffect, useMemo, useState } from "react";
import { getAdminUsers, lockAdminUser } from "../../api/admin.js";
import { useAuth } from "../../context/AuthContext.jsx";
import AdminLayout from "./AdminLayout.jsx";

function formatDateTime(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString("pl-PL");
  } catch {
    return String(value);
  }
}

export default function AdminUsersPage() {
  const { token } = useAuth();
  const [limit] = useState(20);
  const [offset, setOffset] = useState(0);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lockDays, setLockDays] = useState(7);
  const [actionMessage, setActionMessage] = useState(null);
  const [actingUserId, setActingUserId] = useState(null);

  const page = useMemo(() => Math.floor(offset / limit) + 1, [offset, limit]);
  const totalPages = useMemo(() => {
    const total = data?.total ?? 0;
    return Math.max(1, Math.ceil(total / limit));
  }, [data, limit]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminUsers({ token, limit, offset });
      setData(result);
    } catch (e) {
      setError(e.message || "Nie udało się pobrać użytkowników.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset]);

  async function handleLock(userId) {
    setActionMessage(null);
    setActingUserId(userId);
    try {
      const result = await lockAdminUser({ token, userId, days: lockDays });
      setActionMessage(result?.message || "Zablokowano konto.");
      await load();
    } catch (e) {
      setError(e.message || "Nie udało się zablokować konta.");
    } finally {
      setActingUserId(null);
    }
  }

  return (
    <AdminLayout
      title="Użytkownicy"
      subtitle="Zarządzaj dostępem do systemu: blokowanie konta na wybrane dni."
      activeHref="/admin/users"
    >

      {error && (
        <div className="status-card alert" role="alert">
          {error}
        </div>
      )}
      {actionMessage && (
        <div className="status-card" role="status">
          {actionMessage}
        </div>
      )}

      <div className="minor-table-card">
        <div className="minor-table-header">
          <h3>Użytkownicy</h3>
          <div className="admin-controls">
            <label className="field" style={{ margin: 0, minWidth: 240 }}>
              <span>Dni blokady (1–365)</span>
              <input
                type="number"
                min={1}
                max={365}
                value={lockDays}
                onChange={(e) => setLockDays(Number(e.target.value || 7))}
              />
            </label>
          </div>
        </div>

        {loading ? (
          <p style={{ margin: 0 }}>Ładowanie…</p>
        ) : data?.items?.length ? (
          <div className="admin-table-scroll">
            <table className="minor-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Aktywny</th>
                  <th>Superuser</th>
                  <th>Locked until</th>
                  <th>Utworzono</th>
                  <th style={{ textAlign: "right" }}>Akcje</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((u) => (
                  <tr key={u.id}>
                    <td>{u.email}</td>
                    <td>{u.is_active ? "Tak" : "Nie"}</td>
                    <td>{u.is_superuser ? "Tak" : "Nie"}</td>
                    <td>{formatDateTime(u.locked_until)}</td>
                    <td>{formatDateTime(u.created_at)}</td>
                    <td>
                      <div className="minor-table-actions">
                        <button
                          type="button"
                          className="secondary-button"
                          disabled={actingUserId === u.id}
                          onClick={() => {
                            const confirmText = `Zablokować konto użytkownika ${u.email} na ${lockDays} dni?`;
                            if (!window.confirm(confirmText)) return;
                            handleLock(u.id);
                          }}
                        >
                          {actingUserId === u.id ? "Blokowanie…" : "Zablokuj"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ margin: 0 }}>Brak wyników.</p>
        )}

        <div className="actions" style={{ justifyContent: "space-between" }}>
          <button
            type="button"
            className="secondary-button"
            disabled={offset <= 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
          >
            &larr; Poprzednia
          </button>
          <span className="hint" style={{ alignSelf: "center" }}>
            Strona {page} z {totalPages}
          </span>
          <button
            type="button"
            className="secondary-button"
            disabled={data ? offset + limit >= data.total : true}
            onClick={() => setOffset(offset + limit)}
          >
            Następna &rarr;
          </button>
        </div>
      </div>
    </AdminLayout>
  );
}

