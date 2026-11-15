import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { ROLE_RANK, assignableRoles, canAccessRoute, canManageUser, routeGuardFor } from "@/lib/permissions";
import type { User, UserRole } from "@/lib/types";

const person = (role: UserRole, id: string = role): User => ({ id, email: `${id}@example.org`, name: id, role });

test("the ladder matches the plan's ranks", () => {
  expect(ROLE_RANK).toEqual({ STUDENT: 15, RESEARCHER: 30, PROFESSOR: 40, MASTER_ADMIN: 60 });
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

test("a professor assigns only roles below their own", () => {
  expect(assignableRoles(person("PROFESSOR"))).toEqual(["RESEARCHER", "STUDENT"]);
  expect(assignableRoles(person("RESEARCHER"))).toEqual([]);
  expect(assignableRoles(person("MASTER_ADMIN"))).toEqual(["MASTER_ADMIN", "PROFESSOR", "RESEARCHER", "STUDENT"]);
});

test("nobody manages a peer, and another master admin is protected", () => {
  expect(canManageUser(person("PROFESSOR", "a"), person("PROFESSOR", "b"))).toBe(false);
  expect(canManageUser(person("PROFESSOR"), person("STUDENT"))).toBe(true);
  expect(canManageUser(person("MASTER_ADMIN", "a"), person("MASTER_ADMIN", "b"))).toBe(false);
});

test("every gated nav destination has a route guard", () => {
  const nav = readFileSync(join(__dirname, "..", "components", "DynamicIslandNav.tsx"), "utf8");
  const gated = [...nav.matchAll(/href: "(\/admin[^"]*)"/g)].map((match) => match[1]);
  expect(gated.length).toBeGreaterThan(0);
  for (const href of gated) expect(routeGuardFor(href), href).not.toBeNull();
});
