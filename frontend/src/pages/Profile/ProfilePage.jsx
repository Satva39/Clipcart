import { useEffect, useState } from "react";
import {
  FiCheck,
  FiEdit2,
  FiMapPin,
  FiPlus,
  FiTrash2,
  FiUser,
  FiX,
} from "react-icons/fi";
import { useAuth } from "../../context/AuthContext";
import {
  createAddress,
  deleteAddress,
  getAddresses,
  setDefaultAddress,
  updateAddress,
} from "../../services/addressService";
import { getApiMessage } from "../../utils/apiError";
import Container from "../../components/common/Container";
import { LoadingState } from "../../components/common/AsyncState";

const emptyAddress = {
  full_name: "",
  phone: "",
  address_line_1: "",
  address_line_2: "",
  landmark: "",
  city: "",
  state: "",
  postal_code: "",
  country: "India",
  latitude: null,
  longitude: null,
  is_default: false,
};

export default function ProfilePage() {
  const { user, updateProfile, logout } = useAuth();
  const [addresses, setAddresses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [profile, setProfile] = useState(() => ({
    full_name: user?.full_name || "",
    phone: user?.phone || "",
  }));
  const [profileMessage, setProfileMessage] = useState("");
  const [addressModal, setAddressModal] = useState(false);
  const [editingAddress, setEditingAddress] = useState(null);
  const [addressForm, setAddressForm] = useState(emptyAddress);
  const [addressBusy, setAddressBusy] = useState(false);
  const [pageError, setPageError] = useState("");

  useEffect(() => {
    let active = true;
    getAddresses()
      .then((data) => {
        if (active) setAddresses(Array.isArray(data) ? data : []);
      })
      .catch((error) => {
        if (active)
          setPageError(getApiMessage(error, "Couldn't load your addresses."));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function captureAddressLocation() {
    if (!navigator.geolocation) {
      setPageError("This browser does not support location access.");
      return;
    }
    setPageError("");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setAddressForm((current) => ({
          ...current,
          latitude: Number(position.coords.latitude.toFixed(7)),
          longitude: Number(position.coords.longitude.toFixed(7)),
        }));
      },
      () =>
        setPageError(
          "Location permission was unavailable. Enter the address manually.",
        ),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
    );
  }

  async function saveProfile(event) {
    event.preventDefault();
    setSavingProfile(true);
    setProfileMessage("");
    setPageError("");
    try {
      await updateProfile(profile);
      setProfileMessage("Profile updated.");
    } catch (error) {
      setPageError(getApiMessage(error, "Couldn't update your profile."));
    } finally {
      setSavingProfile(false);
    }
  }

  function openAdd() {
    setEditingAddress(null);
    setAddressForm({ ...emptyAddress, full_name: user?.full_name || "" });
    setAddressModal(true);
  }
  function openEdit(address) {
    setEditingAddress(address);
    setAddressForm({ ...emptyAddress, ...address });
    setAddressModal(true);
  }

  async function saveAddress(event) {
    event.preventDefault();
    setAddressBusy(true);
    setPageError("");
    try {
      if (editingAddress) {
        const updated = await updateAddress(editingAddress.id, addressForm);
        setAddresses((current) =>
          current.map((item) =>
            item.id === updated.id
              ? updated
              : addressForm.is_default
                ? { ...item, is_default: false }
                : item,
          ),
        );
      } else {
        const created = await createAddress(addressForm);
        setAddresses((current) =>
          addressForm.is_default
            ? [
                created,
                ...current.map((item) => ({ ...item, is_default: false })),
              ]
            : [created, ...current],
        );
      }
      setAddressModal(false);
    } catch (error) {
      setPageError(getApiMessage(error, "Couldn't save the address."));
    } finally {
      setAddressBusy(false);
    }
  }

  async function makeDefault(id) {
    setPageError("");
    try {
      const updated = await setDefaultAddress(id);
      setAddresses((current) =>
        current.map((item) => ({
          ...item,
          is_default: item.id === updated.id,
        })),
      );
    } catch (error) {
      setPageError(
        getApiMessage(error, "Couldn't change the default address."),
      );
    }
  }

  async function removeAddress(id) {
    if (!window.confirm("Delete this address?")) return;
    try {
      await deleteAddress(id);
      const remaining = addresses.filter((item) => item.id !== id);
      setAddresses(remaining);
    } catch (error) {
      setPageError(getApiMessage(error, "Couldn't delete the address."));
    }
  }

  if (loading)
    return (
      <div className="cc-page-shell">
        <Container>
          <LoadingState label="Loading your account…" />
        </Container>
      </div>
    );

  return (
    <div className="cc-page-shell">
      <Container>
        <div className="cc-page-heading">
          <div>
            <span className="cc-eyebrow">Customer account</span>
            <h1>Your profile</h1>
            <p>Manage your details and delivery addresses.</p>
          </div>
          <button type="button" className="cc-btn secondary" onClick={logout}>
            Sign out
          </button>
        </div>
        {pageError ? (
          <div className="cc-form-error" role="alert">
            {pageError}
          </div>
        ) : null}
        <div className="cc-profile-layout">
          <section className="cc-profile-card">
            <div className="cc-profile-avatar">
              <FiUser />
            </div>
            <div>
              <h2>{user?.full_name}</h2>
              <p>{user?.email}</p>
            </div>
            <div className="cc-account-facts">
              <span>Role</span>
              <strong>Customer</strong>
              <span>Account ID</span>
              <strong>#{user?.id}</strong>
            </div>
          </section>
          <section className="cc-profile-card">
            <div className="cc-card-head">
              <div>
                <h2>Personal details</h2>
                <p>
                  Your email is used as the account login and is not editable
                  here.
                </p>
              </div>
            </div>
            <form className="cc-form compact" onSubmit={saveProfile}>
              <label>
                Full name
                <input
                  value={profile.full_name}
                  onChange={(e) =>
                    setProfile({ ...profile, full_name: e.target.value })
                  }
                  minLength={2}
                  required
                />
              </label>
              <label>
                Phone
                <input
                  value={profile.phone || ""}
                  onChange={(e) =>
                    setProfile({ ...profile, phone: e.target.value })
                  }
                  inputMode="tel"
                />
              </label>
              <label>
                Email
                <input value={user?.email || ""} disabled />
              </label>
              <button
                type="submit"
                className="cc-btn primary"
                disabled={savingProfile}
              >
                {savingProfile ? "Saving…" : "Save changes"}
              </button>
              {profileMessage ? (
                <span className="cc-inline-message">
                  <FiCheck /> {profileMessage}
                </span>
              ) : null}
            </form>
          </section>
          <section className="cc-profile-card wide">
            <div className="cc-card-head">
              <div>
                <h2>Delivery addresses</h2>
                <p>
                  Choose a default address for checkout or keep multiple
                  addresses saved.
                </p>
              </div>
              <button
                type="button"
                className="cc-btn primary"
                onClick={openAdd}
              >
                <FiPlus /> Add address
              </button>
            </div>
            {addresses.length ? (
              <div className="cc-address-grid">
                {addresses.map((address) => (
                  <article
                    key={address.id}
                    className={`cc-address-card${address.is_default ? " default" : ""}`}
                  >
                    <div className="cc-address-top">
                      <span>
                        <FiMapPin />{" "}
                        {address.is_default ? "Default" : "Saved address"}
                      </span>
                      {address.is_default ? <FiCheck /> : null}
                    </div>
                    <strong>{address.full_name}</strong>
                    <p>
                      {address.address_line_1}
                      {address.address_line_2
                        ? `, ${address.address_line_2}`
                        : ""}
                      {address.landmark ? `, ${address.landmark}` : ""}
                    </p>
                    <p>
                      {address.city}, {address.state} {address.postal_code}
                    </p>
                    <p>{address.phone}</p>
                    <div className="cc-inline-actions">
                      {!address.is_default ? (
                        <button
                          type="button"
                          className="cc-link-button"
                          onClick={() => makeDefault(address.id)}
                        >
                          Set default
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="cc-link-button"
                        onClick={() => openEdit(address)}
                      >
                        <FiEdit2 /> Edit
                      </button>
                      <button
                        type="button"
                        className="cc-link-button danger"
                        onClick={() => removeAddress(address.id)}
                      >
                        <FiTrash2 /> Delete
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="cc-slim-empty">
                <span>No saved addresses yet.</span>
                <button
                  type="button"
                  className="cc-text-link"
                  onClick={openAdd}
                >
                  Add your first address →
                </button>
              </div>
            )}
          </section>
        </div>
      </Container>

      {addressModal ? (
        <div
          className="cc-modal-backdrop"
          onClick={() => setAddressModal(false)}
        >
          <div className="cc-modal" onClick={(e) => e.stopPropagation()}>
            <div className="cc-card-head">
              <div>
                <h2>{editingAddress ? "Edit address" : "Add address"}</h2>
                <p>All address fields are stored on your customer account.</p>
              </div>
              <button
                type="button"
                className="cc-icon-btn"
                onClick={() => setAddressModal(false)}
              >
                <FiX />
              </button>
            </div>
            <form className="cc-form compact" onSubmit={saveAddress}>
              <div className="cc-inline-actions">
                <button
                  type="button"
                  className="cc-btn secondary"
                  onClick={captureAddressLocation}
                >
                  <FiMapPin /> Use current location
                </button>
                {addressForm.latitude != null &&
                addressForm.longitude != null ? (
                  <small>
                    Location saved: {addressForm.latitude},{" "}
                    {addressForm.longitude}
                  </small>
                ) : null}
              </div>
              <div className="cc-two-col">
                <label>
                  Full name
                  <input
                    required
                    value={addressForm.full_name}
                    onChange={(e) =>
                      setAddressForm({
                        ...addressForm,
                        full_name: e.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Phone
                  <input
                    required
                    value={addressForm.phone}
                    onChange={(e) =>
                      setAddressForm({ ...addressForm, phone: e.target.value })
                    }
                    inputMode="tel"
                  />
                </label>
                <label>
                  Address line 1
                  <input
                    required
                    value={addressForm.address_line_1}
                    onChange={(e) =>
                      setAddressForm({
                        ...addressForm,
                        address_line_1: e.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Address line 2
                  <input
                    value={addressForm.address_line_2 || ""}
                    onChange={(e) =>
                      setAddressForm({
                        ...addressForm,
                        address_line_2: e.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  Landmark
                  <input
                    value={addressForm.landmark || ""}
                    onChange={(e) =>
                      setAddressForm({
                        ...addressForm,
                        landmark: e.target.value,
                      })
                    }
                  />
                </label>
                <label>
                  City
                  <input
                    required
                    value={addressForm.city}
                    onChange={(e) =>
                      setAddressForm({ ...addressForm, city: e.target.value })
                    }
                  />
                </label>
                <label>
                  State
                  <input
                    required
                    value={addressForm.state}
                    onChange={(e) =>
                      setAddressForm({ ...addressForm, state: e.target.value })
                    }
                  />
                </label>
                <label>
                  Postal code
                  <input
                    required
                    value={addressForm.postal_code}
                    onChange={(e) =>
                      setAddressForm({
                        ...addressForm,
                        postal_code: e.target.value,
                      })
                    }
                    inputMode="numeric"
                  />
                </label>
              </div>
              <label className="cc-check">
                <input
                  type="checkbox"
                  checked={Boolean(addressForm.is_default)}
                  onChange={(e) =>
                    setAddressForm({
                      ...addressForm,
                      is_default: e.target.checked,
                    })
                  }
                />{" "}
                Make this the default address
              </label>
              <div className="cc-modal-actions">
                <button
                  type="button"
                  className="cc-btn secondary"
                  onClick={() => setAddressModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="cc-btn primary"
                  disabled={addressBusy}
                >
                  {addressBusy
                    ? "Saving…"
                    : editingAddress
                      ? "Save address"
                      : "Add address"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
