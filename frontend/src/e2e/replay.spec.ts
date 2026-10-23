import { expect, test } from '@playwright/test';

test('replays the recorded network and resets it', async ({ page }) => {
  await page.goto('/replay');

  await expect(
    page.getByRole('heading', { level: 1, name: 'Recorded replay' }),
  ).toBeVisible();
  await expect(page.getByTestId('replay-label')).toContainText('Grace Wanjiku');
  await expect(
    page.getByText(/\d+ recorded events ready\./),
  ).toBeVisible();

  await page.getByRole('button', { name: 'Fast-forward' }).click();
  await expect(page.getByText(/[1-9]\d* nodes/)).toBeVisible();

  await page.getByRole('button', { name: 'Reset' }).click();
  await expect(page.getByText('0 nodes', { exact: true })).toBeVisible();
  await expect(
    page.getByText('0 events replayed', { exact: true }),
  ).toBeVisible();
});
