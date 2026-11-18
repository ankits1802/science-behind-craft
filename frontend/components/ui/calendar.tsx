"use client";

import { ChevronDownIcon, ChevronLeftIcon, ChevronRightIcon, ChevronUpIcon } from "lucide-react";
import type * as React from "react";
import { DayPicker } from "react-day-picker";
import "react-day-picker/style.css";

import { cn } from "@/lib/utils";

const ROOT_VARS = [
  "[--rdp-selected-border:0]",
  "[--rdp-disabled-opacity:1]",
  "[--rdp-outside-opacity:1]",
  "[--rdp-weekday-opacity:1]",
  "[--rdp-week_number-opacity:1]",
  "[--rdp-day-height:2.25rem]",
  "[--rdp-day-width:2.25rem]",
  "[--rdp-day_button-height:2.25rem]",
  "[--rdp-day_button-width:2.25rem]",
  "[--rdp-day_button-border:0]",
  "[--rdp-day_button-border-radius:4px]",
  "[--rdp-nav_button-height:2rem]",
  "[--rdp-nav_button-width:2rem]",
  "[--rdp-nav-height:2.25rem]",
  "[--rdp-months-gap:1.5rem]"
].join(" ");

const NAV_BUTTON =
  "relative inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-control text-ink-2 transition-colors duration-state " +
  "hover:bg-sunk hover:text-ink-1 disabled:pointer-events-none disabled:text-ink-3 " +
  "[&_svg]:pointer-events-none [&_svg]:h-4 [&_svg]:w-4 [&_svg]:shrink-0";

const DAY_BUTTON =
  "relative mx-auto flex h-9 w-9 cursor-pointer items-center justify-center rounded-control font-ui text-ui tabular-nums transition-colors duration-state hover:bg-sunk";

export function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  components: userComponents,
  mode = "single",
  ...props
}: React.ComponentProps<typeof DayPicker>): React.ReactElement {
  const defaultClassNames = {
    months: "relative flex flex-col gap-4 sm:flex-row",
    month: "space-y-2",
    month_caption: "flex h-9 items-center justify-center",
    caption_label: "flex h-full items-center gap-2 font-ui text-ui font-semibold text-ink-1",
    nav: "absolute inset-x-0 top-0 flex h-9 items-center justify-between",
    button_previous: NAV_BUTTON,
    button_next: NAV_BUTTON,
    dropdowns: "flex items-center gap-2",
    dropdown_root:
      "relative flex h-8 items-center rounded-control border border-rule-strong bg-raised px-2 font-ui text-ui text-ink-1 transition-colors duration-state " +
      "focus-within:border-indigo focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-indigo",
    dropdown: "absolute inset-0 cursor-pointer opacity-0",
    month_grid: "w-full border-collapse",
    weekday: "h-8 w-9 p-0 font-ui text-caption font-semibold text-ink-3",
    week_number_header: "h-8 w-9 p-0 font-ui text-caption font-semibold text-ink-3",
    week_number: "h-9 w-9 p-0 text-center font-ui text-caption tabular-nums text-ink-3",
    day: "h-9 w-9 p-0 text-center align-middle font-ui text-ui text-ink-1",
    day_button: DAY_BUTTON,
    selected: "[&>button]:bg-indigo [&>button]:font-semibold [&>button]:text-indigo-on hover:[&>button]:bg-indigo-hover",
    range_start: "rounded-s-control bg-indigo-wash",
    range_end: "rounded-e-control bg-indigo-wash",
    range_middle: "bg-indigo-wash [&>button]:rounded-none! [&>button]:bg-transparent! [&>button]:font-normal! [&>button]:text-ink-1!",
    today:
      "[&:not([data-selected])>button]:font-semibold [&:not([data-selected])>button]:text-indigo " +
      "[&:not([data-selected])>button]:ring-1 [&:not([data-selected])>button]:ring-inset [&:not([data-selected])>button]:ring-rule-strong",
    outside: "[&:not([data-selected])>button]:font-normal [&:not([data-selected])>button]:text-ink-3",
    disabled: "[&>button]:cursor-not-allowed [&>button]:text-ink-3 hover:[&>button]:bg-transparent",
    hidden: "invisible",
    footer: "pt-2 font-ui text-caption text-ink-3"
  };

  const mergedClassNames = Object.keys(defaultClassNames).reduce(
    (acc, key) => {
      const userClass = classNames?.[key as keyof typeof classNames];
      const baseClass = defaultClassNames[key as keyof typeof defaultClassNames];
      acc[key as keyof typeof defaultClassNames] = userClass ? cn(baseClass, userClass) : baseClass;
      return acc;
    },
    { ...defaultClassNames }
  );

  const defaultComponents = {
    Chevron: ({
      className: iconClassName,
      orientation,
      ...iconProps
    }: {
      className?: string;
      orientation?: "left" | "right" | "up" | "down";
    }) => {
      if (orientation === "left") return <ChevronLeftIcon className={cn(iconClassName, "rtl:rotate-180")} {...iconProps} aria-hidden="true" />;
      if (orientation === "right") return <ChevronRightIcon className={cn(iconClassName, "rtl:rotate-180")} {...iconProps} aria-hidden="true" />;
      if (orientation === "up") return <ChevronUpIcon className={iconClassName} {...iconProps} aria-hidden="true" />;
      return <ChevronDownIcon className={iconClassName} {...iconProps} aria-hidden="true" />;
    }
  };

  return (
    <DayPicker
      className={cn("w-fit font-ui text-ink-1", ROOT_VARS, className)}
      classNames={mergedClassNames}
      components={{ ...defaultComponents, ...userComponents }}
      formatters={{ formatMonthDropdown: (date: Date) => date.toLocaleString("default", { month: "short" }) }}
      mode={mode}
      showOutsideDays={showOutsideDays}
      {...(props as React.ComponentProps<typeof DayPicker>)}
    />
  );
}
