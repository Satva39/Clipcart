import { FiEye, FiEyeOff } from "react-icons/fi";
import { useId, useState } from "react";

export default function PasswordInput({ leadingIcon, id, ...props }) {
  const generatedId = useId();
  const inputId = id || generatedId;
  const [visible, setVisible] = useState(false);
  return (
    <span className="cc-input-icon cc-password-field">
      {leadingIcon}
      <input {...props} id={inputId} type={visible ? "text" : "password"} />
      <button
        type="button"
        className="cc-password-toggle"
        onClick={() => setVisible((current) => !current)}
        aria-label={visible ? "Hide password" : "Show password"}
        aria-pressed={visible}
      >
        {visible ? <FiEyeOff /> : <FiEye />}
      </button>
    </span>
  );
}
