import { Moon, Sun } from "lucide-react";

interface Props {
  dark: boolean;
  onToggle: () => void;
}

function ThemeToggle({ dark, onToggle }: Props) {
  return (
    <button
      onClick={onToggle}
      style={{
        width: 42,
        height: 42,
        borderRadius: 12,
        border: "1px solid var(--border)",
        background: "var(--card)",
        color: "var(--text)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
      }}
    >
      {dark ? <Sun size={20} /> : <Moon size={20} />}
    </button>
  );
}

export default ThemeToggle;