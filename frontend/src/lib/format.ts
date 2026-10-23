const decimal = new Intl.NumberFormat('en-KE', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const money = new Intl.NumberFormat('en-KE', {
  maximumFractionDigits: 0,
});

export function formatScore(value: number | null, digits = 1): string {
  if (value === null) {
    return '—';
  }
  return digits === 1 ? decimal.format(value) : value.toFixed(digits);
}

export function formatMoney(value: number | null): string {
  if (value === null) {
    return '—';
  }
  return money.format(value);
}

export function formatPercent(value: number | null): string {
  if (value === null) {
    return '—';
  }
  return `${Math.round(value * 100)}%`;
}

export function formatCount(value: number): string {
  return money.format(value);
}

export function titleCase(value: string | null): string {
  if (!value) {
    return 'Unscored';
  }
  const lower = value.replace(/_/g, ' ').toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

export function decisionTone(decision: string | null): string {
  if (decision === 'ELIGIBLE') {
    return 'good';
  }
  if (decision === 'REVIEW_REQUIRED') {
    return 'warn';
  }
  if (decision === 'DECLINE') {
    return 'bad';
  }
  return 'muted';
}
