export default function Container({ className = "", children }) {
  return <div className={`cc-container ${className}`.trim()}>{children}</div>;
}
