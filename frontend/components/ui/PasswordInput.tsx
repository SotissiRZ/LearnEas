"use client";

import { useState, forwardRef } from "react";
import { Eye, EyeOff, Lock } from "lucide-react";

interface Props extends React.InputHTMLAttributes<HTMLInputElement> {
  showIcon?: boolean;
}

/** Champ mot de passe avec bouton œil pour afficher/masquer la saisie. */
const PasswordInput = forwardRef<HTMLInputElement, Props>(function PasswordInput(
  { showIcon = true, className, ...props },
  ref
) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="relative">
      {showIcon && <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />}
      <input
        {...props}
        ref={ref}
        type={visible ? "text" : "password"}
        className={
          className ||
          `w-full rounded-lg border border-gray-200 py-2.5 ${showIcon ? "pl-10" : "pl-3"} pr-10 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100`
        }
      />
      <button
        type="button"
        tabIndex={-1}
        onClick={() => setVisible((v) => !v)}
        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
        aria-label={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"}
      >
        {visible ? <EyeOff size={18} /> : <Eye size={18} />}
      </button>
    </div>
  );
});

export default PasswordInput;
