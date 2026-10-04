import { useEffect, useState } from "react";
import {
  FaBuilding,
  FaCheckCircle,
  FaShieldAlt,
  FaUser,
  FaWallet,
  FaMapMarkerAlt,
} from "react-icons/fa";
import {
  getSupplierProfile,
  updateSupplierProfile,
} from "../../services/portalService";
import {
  getPayoutAccount,
  savePayoutAccount,
} from "../../services/payoutService";
import "../../styles/supplier-pages.css";

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({
    full_name: "",
    phone: "",
    business_name: "",
    gst_number: "",
    return_address: {
      address_line_1: "",
      address_line_2: "",
      landmark: "",
      city: "",
      state: "",
      postal_code: "",
      country: "India",
    },
  });
  const [payout, setPayout] = useState({
    holder_name: "",
    bank_name: "",
    account_number: "",
    ifsc: "",
    upi_id: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function load() {
    setLoading(true);
    try {
      const [p, a] = await Promise.all([
        getSupplierProfile(),
        getPayoutAccount(),
      ]);
      setProfile(p);
      setForm({
        full_name: p?.account?.full_name || "",
        phone: p?.account?.phone || "",
        business_name: p?.business?.business_name || "",
        gst_number: p?.business?.gst_number || "",
        return_address: {
          address_line_1: p?.business?.return_address?.address_line_1 || "",
          address_line_2: p?.business?.return_address?.address_line_2 || "",
          landmark: p?.business?.return_address?.landmark || "",
          city: p?.business?.return_address?.city || "",
          state: p?.business?.return_address?.state || "",
          postal_code: p?.business?.return_address?.postal_code || "",
          country: p?.business?.return_address?.country || "India",
        },
      });
      if (a)
        setPayout({
          holder_name: a.holder_name || "",
          bank_name: a.bank_name || "",
          account_number: "",
          ifsc: a.ifsc || "",
          upi_id: a.upi_id || "",
        });
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to load profile.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
  }, []);
  async function save(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await updateSupplierProfile(form);
      await savePayoutAccount(payout);
      setMessage("Profile and payout settings saved.");
      await load();
    } catch (e) {
      setError(e?.response?.data?.message || "Unable to save settings.");
    } finally {
      setSaving(false);
    }
  }
  return (
    <div className="page-shell">
      <div className="page-heading">
        <div>
          <h2>Profile & settings</h2>
          <p>
            Manage the supplier information that you are permitted to change.
          </p>
        </div>
      </div>
      {error && <div className="notice error">{error}</div>}
      {message && <div className="notice success">{message}</div>}
      {loading ? (
        <div className="panel empty-state">Loading profile…</div>
      ) : (
        <form onSubmit={save}>
          <div className="profile-grid-pro">
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h3 className="panel-title">
                    <FaUser /> Account
                  </h3>
                  <p className="panel-subtitle">
                    Login identity and contact details.
                  </p>
                </div>
              </div>
              <div className="form-card">
                <label className="form-label">
                  Full name
                  <input
                    className="form-control"
                    value={form.full_name}
                    onChange={(e) =>
                      setForm({ ...form, full_name: e.target.value })
                    }
                    required
                  />
                </label>
                <label className="form-label">
                  Email
                  <input
                    className="form-control"
                    value={profile?.account?.email || ""}
                    disabled
                  />
                </label>
                <label className="form-label">
                  Phone
                  <input
                    className="form-control"
                    value={form.phone}
                    onChange={(e) =>
                      setForm({ ...form, phone: e.target.value })
                    }
                  />
                </label>
                <div className="profile-state">
                  <span>Account status</span>
                  <b>{profile?.account?.status}</b>
                </div>
              </div>
            </section>
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h3 className="panel-title">
                    <FaBuilding /> Business
                  </h3>
                  <p className="panel-subtitle">
                    Business verification data and registration status.
                  </p>
                </div>
                <span
                  className={`status-chip ${profile?.business?.verification_status === "APPROVED" ? "success" : "warning"}`}
                >
                  {profile?.business?.verification_status || "PENDING"}
                </span>
              </div>
              <div className="form-card">
                <label className="form-label">
                  Business name
                  <input
                    className="form-control"
                    value={form.business_name}
                    onChange={(e) =>
                      setForm({ ...form, business_name: e.target.value })
                    }
                    required
                  />
                </label>
                <label className="form-label">
                  GST number
                  <input
                    className="form-control"
                    value={form.gst_number}
                    onChange={(e) =>
                      setForm({ ...form, gst_number: e.target.value })
                    }
                  />
                </label>
                <div className="profile-state">
                  <span>Registration fee</span>
                  <b>
                    <FaCheckCircle />{" "}
                    {profile?.business?.registration_fee_paid
                      ? "Paid"
                      : "Pending"}
                  </b>
                </div>
              </div>
            </section>
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h3 className="panel-title">
                    <FaWallet /> Payout settings
                  </h3>
                  <p className="panel-subtitle">
                    Only permitted payout fields are editable here.
                  </p>
                </div>
                <span
                  className={`status-chip ${profile?.payout?.is_verified ? "success" : "warning"}`}
                >
                  {profile?.payout?.is_verified ? "VERIFIED" : "NOT VERIFIED"}
                </span>
              </div>
              <div className="form-card">
                <div className="form-grid-2">
                  <Field
                    label="Holder name"
                    v="holder_name"
                    state={payout}
                    set={setPayout}
                  />
                  <Field
                    label="Bank name"
                    v="bank_name"
                    state={payout}
                    set={setPayout}
                  />
                  <Field
                    label="Account number"
                    v="account_number"
                    state={payout}
                    set={setPayout}
                    placeholder={
                      profile?.payout?.account_number || "Enter account number"
                    }
                  />
                  <Field label="IFSC" v="ifsc" state={payout} set={setPayout} />
                  <Field
                    label="UPI ID"
                    v="upi_id"
                    state={payout}
                    set={setPayout}
                  />
                </div>
              </div>
            </section>
            <section className="panel profile-return-address-panel">
              <div className="panel-header">
                <div>
                  <h3 className="panel-title">
                    <FaMapMarkerAlt /> Return / warehouse address
                  </h3>
                  <p className="panel-subtitle">
                    This is the destination used when logistics returns a
                    customer item to you.
                  </p>
                </div>
              </div>
              <div className="form-card">
                <label className="form-label">
                  Address line 1
                  <input
                    className="form-control"
                    value={form.return_address.address_line_1}
                    onChange={(e) =>
                      setForm((x) => ({
                        ...x,
                        return_address: {
                          ...x.return_address,
                          address_line_1: e.target.value,
                        },
                      }))
                    }
                  />
                </label>
                <label className="form-label">
                  Address line 2
                  <input
                    className="form-control"
                    value={form.return_address.address_line_2}
                    onChange={(e) =>
                      setForm((x) => ({
                        ...x,
                        return_address: {
                          ...x.return_address,
                          address_line_2: e.target.value,
                        },
                      }))
                    }
                  />
                </label>
                <div className="form-grid-2">
                  <label className="form-label">
                    Landmark
                    <input
                      className="form-control"
                      value={form.return_address.landmark}
                      onChange={(e) =>
                        setForm((x) => ({
                          ...x,
                          return_address: {
                            ...x.return_address,
                            landmark: e.target.value,
                          },
                        }))
                      }
                    />
                  </label>
                  <label className="form-label">
                    City
                    <input
                      className="form-control"
                      value={form.return_address.city}
                      onChange={(e) =>
                        setForm((x) => ({
                          ...x,
                          return_address: {
                            ...x.return_address,
                            city: e.target.value,
                          },
                        }))
                      }
                    />
                  </label>
                  <label className="form-label">
                    State
                    <input
                      className="form-control"
                      value={form.return_address.state}
                      onChange={(e) =>
                        setForm((x) => ({
                          ...x,
                          return_address: {
                            ...x.return_address,
                            state: e.target.value,
                          },
                        }))
                      }
                    />
                  </label>
                  <label className="form-label">
                    Postal code
                    <input
                      className="form-control"
                      value={form.return_address.postal_code}
                      onChange={(e) =>
                        setForm((x) => ({
                          ...x,
                          return_address: {
                            ...x.return_address,
                            postal_code: e.target.value,
                          },
                        }))
                      }
                    />
                  </label>
                  <label className="form-label">
                    Country
                    <input
                      className="form-control"
                      value={form.return_address.country}
                      onChange={(e) =>
                        setForm((x) => ({
                          ...x,
                          return_address: {
                            ...x.return_address,
                            country: e.target.value,
                          },
                        }))
                      }
                    />
                  </label>
                </div>
              </div>
            </section>
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h3 className="panel-title">
                    <FaShieldAlt /> Account protection
                  </h3>
                  <p className="panel-subtitle">
                    Restricted internal/admin data is never surfaced in the
                    supplier portal.
                  </p>
                </div>
              </div>
              <div className="form-card">
                <div className="security-callout">
                  <b>Supplier-scoped access</b>
                  <span>
                    Your API session is checked against the supplier role and
                    live account status before sensitive portal data is
                    returned.
                  </span>
                </div>
              </div>
            </section>
          </div>
          <button className="action-link" disabled={saving}>
            {saving ? "Saving settings…" : "Save changes"}
          </button>
        </form>
      )}
    </div>
  );
}
function Field({ label, v, state, set, placeholder }) {
  return (
    <label className="form-label">
      {label}
      <input
        className="form-control"
        name={v}
        value={state[v] || ""}
        placeholder={placeholder}
        onChange={(e) => set((x) => ({ ...x, [v]: e.target.value }))}
      />
    </label>
  );
}
