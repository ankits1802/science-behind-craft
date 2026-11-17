const POSITIVE = /^[1-9]\d{0,8}$/;

export function positiveParam(value: string | null): number | null {
  return value && POSITIVE.test(value) ? Number(value) : null;
}
