import { useEffect, useState } from "react";
import { getAuditLogs } from "../services/auditService";

export default function AuditLogs() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setData(await getAuditLogs());
      } catch (err) {
        setError(err?.response?.data?.message || "Unable to load audit log.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);
  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <span className="admin-eyebrow">SECURITY & ACCOUNTABILITY</span>
        <h1>Audit log</h1>
        <p>
          Important administrative changes are recorded with the resource type
          and action.
        </p>
      </div>
      {error && <div className="admin-error">{error}</div>}
      <div className="admin-table-card">
        <div className="admin-table-wrap">
          {loading ? (
            <div className="admin-empty">Loading audit log…</div>
          ) : !data?.logs?.length ? (
            <div className="admin-empty">
              No administrative actions have been recorded.
            </div>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Resource</th>
                  <th>Metadata</th>
                </tr>
              </thead>
              <tbody>
                {data.logs.map((x) => (
                  <tr key={x.id}>
                    <td>
                      {x.created_at
                        ? new Date(x.created_at).toLocaleString("en-IN")
                        : "—"}
                    </td>
                    <td>
                      <strong>{x.action}</strong>
                    </td>
                    <td>
                      {x.resource_type}
                      <span>{x.resource_id || "—"}</span>
                    </td>
                    <td>
                      <code>{JSON.stringify(x.metadata || {})}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
