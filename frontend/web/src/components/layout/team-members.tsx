"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { useAuth } from "@/components/auth/auth-context";
import { ChevronsUpDown, Check } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { getUserPhoto } from "@/lib/user-photo-storage";

type TeamMember = {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  role: string;
  isActive: boolean;
};

type TeamMembersProps = {
  showCurrentUserOnly?: boolean;
};

function initialsFor(nameOrEmail: string) {
  const base = nameOrEmail.trim();
  if (!base) return "?";
  const parts = base.includes("@") ? base.split("@")[0].split(/[.\s_-]+/) : base.split(/\s+/);
  return parts
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

export function TeamMembers({ showCurrentUserOnly = false }: TeamMembersProps) {
  const { t } = useTranslation();
  const { email, role } = useAuth();
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  const { data: teamMembers = [], isError } = useQuery<TeamMember[]>({
    queryKey: ["team-members"],
    queryFn: async () => {
      const members = await api.getTeamMembers();
      return members;
    },
    staleTime: 60_000,
    retry: false,
  });

  const currentUser = email
    ? {
        id: "current-user",
        name: email.split("@")[0] || email,
        email,
        role: role === "admin" ? "admin" : "analyst",
        isActive: true,
      }
    : null;

  const otherMembers = teamMembers.filter((m) => m.email !== email);

  if (showCurrentUserOnly && currentUser) {
    const userPhoto = getUserPhoto();
    return (
      <div className="flex items-center gap-3 rounded-lg px-3 py-2 transition hover:bg-[var(--surface-2)]">
        <div className="relative flex h-12 w-12 flex-shrink-0 items-center justify-center overflow-hidden rounded-full border border-[var(--surface-3)] bg-[var(--surface-2)] text-xs font-semibold text-[var(--ink-2)]">
          {userPhoto ? (
            <img src={userPhoto} alt={currentUser.name} className="h-full w-full object-cover" />
          ) : (
            initialsFor(currentUser.email)
          )}
          <div className="absolute bottom-0 right-0 h-4 w-4 rounded-full border-2 border-[var(--surface-1)] bg-[var(--accent-success)]" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="truncate text-sm font-medium text-[var(--ink-1)]">{currentUser.name}</p>
          <p className="truncate text-xs text-[var(--ink-3)]">{currentUser.email}</p>
        </div>
        <ChevronsUpDown className="h-4 w-4 text-[var(--ink-3)]" />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="px-3 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--ink-3)]">
        {t("team.title", { defaultValue: "Team members" })}
      </p>
      {isError ? (
        <div className="rounded-lg border border-[var(--surface-3)] bg-[var(--surface-2)] px-3 py-2 text-xs text-[var(--ink-3)]">
          {t("team.unavailable", { defaultValue: "Team members unavailable." })}
        </div>
      ) : null}
      {otherMembers.map((member) => {
        const isSelected = selectedUserId === member.id;
        return (
          <button
            key={member.id}
            onClick={() => setSelectedUserId(member.id)}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition ${
              isSelected
                ? "bg-[var(--accent-1)]/10"
                : "hover:bg-[var(--surface-2)]"
            }`}
          >
            <div className="relative flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-[var(--surface-3)] bg-[var(--surface-1)] text-xs font-semibold text-[var(--ink-2)]">
              {initialsFor(member.name || member.email)}
              {member.isActive ? (
                <div className="absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-[var(--surface-1)] bg-[var(--accent-success)]" />
              ) : null}
            </div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-medium text-[var(--ink-1)]">{member.name}</p>
              <p className="truncate text-xs text-[var(--ink-3)]">{member.email}</p>
            </div>
            {isSelected && (
              <Check className="h-4 w-4 flex-shrink-0 text-[var(--accent-1)]" />
            )}
          </button>
        );
      })}
    </div>
  );
}
