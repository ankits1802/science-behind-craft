import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { rowOffers } from "@/app/(protected)/admin/users/userAdmin";
import { accessEntryOffers, type AccessRosterEntry } from "@/lib/accessRoster";
import {
  ROLE_LABELS,
  ROLE_RANK,
  assignableRoles,
  canAccessRoute,
  canManageUser,
  roleLabel,
  routeGuardFor
} from "@/lib/permissions";
import type { User, UserRole } from "@/lib/types";

const person = (role: UserRole, id: string = role): User => ({ id, email: `${id}@example.org`, name: id, role });

const LADDER: UserRole[] = ["STUDENT", "RESEARCHER", "PROFESSOR", "ADMIN", "MASTER_ADMIN"];

const NAV_SOURCE = readFileSync(join(__dirname, "..", "components", "DynamicIslandNav.tsx"), "utf8");
const ADMIN_NAV_HREFS = [...NAV_SOURCE.matchAll(/href: "(\/admin[^"]*)"/g)].map((match) => match[1]);

const SHARED_ROLES = JSON.parse(readFileSync(join(__dirname, "..", "..", "shared", "roles.json"), "utf8")) as {
  ranks: Record<string, number>;
  labels: Record<string, string>;
};

function rosterEntry(admitRole: UserRole | null, status: AccessRosterEntry["status"]): AccessRosterEntry {
  return {
    id: `${admitRole ?? "default"}-${status}`,
    email: "entry@example.org",
    fullName: null,
    status,
    admitRole,
    joinedAt: null,
    requestedAt: null,
    attemptCount: 0,
    lastAttemptAt: null,
    decidedAt: null,
    decidedById: null,
    firstSeenAt: null,
    notes: null,
    createdAt: null,
    updatedAt: null,
    addedById: null
  };
}

test("the ladder matches the plan's ranks", () => {
  expect(ROLE_RANK).toEqual({ STUDENT: 15, RESEARCHER: 30, PROFESSOR: 40, ADMIN: 50, MASTER_ADMIN: 60 });
});

test("ranks and labels agree with the shared roles file", () => {
  expect(ROLE_RANK).toEqual(SHARED_ROLES.ranks);
  expect(ROLE_LABELS).toEqual(SHARED_ROLES.labels);
});

test("the admin role reads as Admin", () => {
  expect(roleLabel("ADMIN")).toBe("Admin");
  expect(roleLabel("MASTER_ADMIN")).toBe("Master Admin");
});

test("the longest guard wins, so a professor reaches the roster but not the hub", () => {
  const professor = person("PROFESSOR");
  expect(routeGuardFor("/admin/access")?.path).toBe("/admin/access");
  expect(canAccessRoute(professor, "/admin/access")).toBe(true);
  expect(canAccessRoute(professor, "/admin/users")).toBe(true);
  expect(canAccessRoute(professor, "/admin")).toBe(false);
  expect(canAccessRoute(professor, "/admin/keys")).toBe(false);
  expect(canAccessRoute(person("STUDENT"), "/admin/access")).toBe(false);
  expect(canAccessRoute(person("MASTER_ADMIN"), "/admin/routing")).toBe(true);
});

test("each role sees exactly the admin destinations it is entitled to", () => {
  const expected: Record<UserRole, string[]> = {
    STUDENT: [],
    RESEARCHER: [],
    PROFESSOR: ["/admin/access", "/admin/users"],
    ADMIN: ["/admin", "/admin/access", "/admin/users", "/admin/usage"],
    MASTER_ADMIN: ["/admin", "/admin/access", "/admin/users", "/admin/keys", "/admin/routing", "/admin/usage"]
  };
  for (const role of LADDER) {
    const visible = ADMIN_NAV_HREFS.filter((href) => canAccessRoute(person(role), href));
    expect(visible, role).toEqual(expected[role]);
  }
});

test("every admin nav destination is shown by its own route guard", () => {
  expect(ADMIN_NAV_HREFS.length).toBeGreaterThan(0);
  for (const href of ADMIN_NAV_HREFS) {
    expect(routeGuardFor(href), href).not.toBeNull();
    const entry = new RegExp(`href: "${href}"[^}]*can: routeAllows\\("${href}"\\)`);
    expect(NAV_SOURCE, href).toMatch(entry);
  }
});

test("roles are assigned only below one's own, and the master admin assigns Admin", () => {
  expect(assignableRoles(person("PROFESSOR"))).toEqual(["RESEARCHER", "STUDENT"]);
  expect(assignableRoles(person("ADMIN"))).toEqual(["PROFESSOR", "RESEARCHER", "STUDENT"]);
  expect(assignableRoles(person("RESEARCHER"))).toEqual([]);
  expect(assignableRoles(person("MASTER_ADMIN"))).toEqual(["MASTER_ADMIN", "ADMIN", "PROFESSOR", "RESEARCHER", "STUDENT"]);
});

test("nobody manages a peer, and another master admin is protected", () => {
  expect(canManageUser(person("PROFESSOR", "a"), person("PROFESSOR", "b"))).toBe(false);
  expect(canManageUser(person("PROFESSOR"), person("STUDENT"))).toBe(true);
  expect(canManageUser(person("MASTER_ADMIN", "a"), person("MASTER_ADMIN", "b"))).toBe(false);
  expect(canManageUser(person("ADMIN"), person("PROFESSOR"))).toBe(true);
  expect(canManageUser(person("ADMIN", "a"), person("ADMIN", "b"))).toBe(false);
  expect(canManageUser(person("ADMIN"), person("MASTER_ADMIN"))).toBe(false);
  expect(canManageUser(person("MASTER_ADMIN"), person("ADMIN"))).toBe(true);
});

test("an admin is offered every action on a professor and none on an admin or the master admin", () => {
  const admin = person("ADMIN", "viewer");
  const professor = { ...person("PROFESSOR", "prof"), twoFactorEnabled: true };
  expect(rowOffers(admin, professor)).toEqual({ role: true, suspend: true, reactivate: false, resetTwoStep: true });
  const none = { role: false, suspend: false, reactivate: false, resetTwoStep: false };
  expect(rowOffers(admin, { ...person("ADMIN", "peer"), twoFactorEnabled: true })).toEqual(none);
  expect(rowOffers(admin, { ...person("MASTER_ADMIN", "owner"), twoFactorEnabled: true })).toEqual(none);
  expect(rowOffers(person("PROFESSOR", "p"), { ...person("STUDENT", "s"), twoFactorEnabled: true })).toEqual({
    role: false,
    suspend: false,
    reactivate: false,
    resetTwoStep: false
  });
});

test("roster actions follow the entry's role and the viewer's rank", () => {
  const admin = person("ADMIN");
  const professor = person("PROFESSOR");
  const none = { update: false, suspend: false, admit: false, refuse: false };
  expect(accessEntryOffers(admin, rosterEntry("ADMIN", "ACTIVE"))).toEqual(none);
  expect(accessEntryOffers(admin, rosterEntry("MASTER_ADMIN", "ACTIVE"))).toEqual(none);
  expect(accessEntryOffers(admin, rosterEntry("PROFESSOR", "ACTIVE"))).toEqual({ update: true, suspend: true, admit: false, refuse: false });
  expect(accessEntryOffers(admin, rosterEntry("PROFESSOR", "SUSPENDED"))).toEqual({ update: true, suspend: false, admit: true, refuse: false });
  expect(accessEntryOffers(admin, rosterEntry(null, "PENDING"))).toEqual({ update: true, suspend: false, admit: true, refuse: true });
  expect(accessEntryOffers(professor, rosterEntry("STUDENT", "SUSPENDED"))).toEqual({ update: true, suspend: false, admit: false, refuse: false });
  expect(accessEntryOffers(professor, rosterEntry("PROFESSOR", "ACTIVE"))).toEqual(none);
  expect(accessEntryOffers(person("MASTER_ADMIN"), rosterEntry("ADMIN", "ACTIVE"))).toEqual({ update: true, suspend: true, admit: false, refuse: false });
});
