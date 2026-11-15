"use client";

import { Children, isValidElement, useId, useMemo, useState, type ReactNode, type SelectHTMLAttributes } from "react";

import { Dropdown, type DropdownOption } from "@/components/ui/Dropdown";
import { FieldLabelProvider } from "@/components/ui/fieldLabel";
import { RequiredMark } from "@/components/ui/RequiredMark";

export function Field({
  label,
  children,
  required,
  fieldKey
}: {
  label: string;
  children: React.ReactNode;
  required?: boolean;
  fieldKey?: string;
}) {
  const labelId = useId();
  return (
    <label className="grid min-w-0 content-start gap-1" data-field={fieldKey}>
      <span id={labelId} className="field-label">
        {label}
        <RequiredMark when={required} />
      </span>
      <FieldLabelProvider value={labelId}>{children}</FieldLabelProvider>
    </label>
  );
}

export function FieldBlock({
  label,
  required,
  hint,
  children,
  fieldKey
}: {
  label: string;
  required?: boolean;
  hint?: React.ReactNode;
  children: React.ReactNode;
  fieldKey?: string;
}) {
  const id = useId();
  return (
    <div className="grid min-w-0 gap-1" data-field={fieldKey}>
      <span id={id} className="field-label">
        {label}
        <RequiredMark when={required} />
      </span>
      <div role="group" aria-labelledby={id}>
        <FieldLabelProvider value={id}>{children}</FieldLabelProvider>
      </div>
      {hint}
    </div>
  );
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`field-input ${props.className ?? ""}`} />;
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`field-input min-h-24 ${props.className ?? ""}`} />;
}

function optionText(node: ReactNode): string {
  if (node === null || node === undefined || typeof node === "boolean") return "";
  if (typeof node === "string") return node;
  if (typeof node === "number" || typeof node === "bigint") return String(node);
  if (Array.isArray(node)) return (node as ReactNode[]).map(optionText).join("");
  if (isValidElement(node)) return optionText((node.props as { children?: ReactNode }).children);
  return "";
}

function optionsFromChildren(children: ReactNode): DropdownOption[] {
  const options: DropdownOption[] = [];
  Children.forEach(children, (child) => {
    if (!isValidElement(child) || child.type !== "option") return;
    const props = child.props as { value?: string | number; children?: ReactNode; disabled?: boolean };
    const text = optionText(props.children).replace(/\s+/g, " ").trim();
    const label = text || (props.value !== undefined ? String(props.value) : "");
    const value = props.value !== undefined ? String(props.value) : label;
    options.push({ value, label, disabled: props.disabled });
  });
  return options;
}

type SelectProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "defaultValue" | "onChange" | "type" | "children"> & {
  value?: SelectHTMLAttributes<HTMLSelectElement>["value"];
  defaultValue?: SelectHTMLAttributes<HTMLSelectElement>["value"];
  onChange?: React.ChangeEventHandler<HTMLSelectElement>;
  children?: ReactNode;
  searchable?: boolean;
  advanceOnSelect?: boolean;
  emptyLabel?: string;
};

export function Select({
  name,
  value,
  defaultValue,
  onChange,
  disabled,
  required,
  className,
  children,
  placeholder,
  emptyLabel,
  searchable,
  advanceOnSelect,
  "aria-label": ariaLabel,
  "aria-describedby": ariaDescribedBy,
  ...rest
}: SelectProps) {
  const options = useMemo(() => optionsFromChildren(children), [children]);
  const isControlled = value !== undefined;
  const [internal, setInternal] = useState<string>(() => {
    if (defaultValue !== undefined) return String(defaultValue);
    if (value !== undefined) return String(value);
    return options[0]?.value ?? "";
  });
  const current = isControlled ? String(value) : internal;

  function handleChange(next: string) {
    if (!isControlled) setInternal(next);
    onChange?.({ target: { value: next, name } } as unknown as React.ChangeEvent<HTMLSelectElement>);
  }

  return (
    <>
      <Dropdown
        value={current}
        onChange={handleChange}
        options={options}
        {...(placeholder === undefined ? {} : { placeholder })}
        emptyLabel={emptyLabel}
        searchable={searchable}
        {...(advanceOnSelect === undefined ? {} : { advanceOnSelect })}
        disabled={disabled}
        className={className}
        ariaLabel={typeof ariaLabel === "string" ? ariaLabel : undefined}
        describedBy={typeof ariaDescribedBy === "string" ? ariaDescribedBy : undefined}
      />
      {name ? (
        <input
          {...rest}
          type="text"
          name={name}
          value={current}
          required={required}
          onChange={() => undefined}
          tabIndex={-1}
          aria-hidden="true"
          className="pointer-events-none absolute h-0 w-0 border-0 p-0 opacity-0"
        />
      ) : null}
    </>
  );
}
