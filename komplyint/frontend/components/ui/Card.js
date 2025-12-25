export default function Card({ children, className = "", variant = "default" }) {
  const bgClass = variant === "green" 
    ? "bg-green-50 border-green-100" 
    : variant === "blue" 
    ? "bg-blue-50 border-blue-100" 
    : "bg-white/70 border-slate-200";
  
  return (
    <div
      className={`rounded-lg border p-6 shadow-sm ${bgClass} ${className}`.trim()}
    >
      {children}
    </div>
  );
}
