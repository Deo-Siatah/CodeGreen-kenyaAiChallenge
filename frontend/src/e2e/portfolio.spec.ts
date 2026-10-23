import { expect, test } from '@playwright/test';
import {
  createScoredFarmer,
  newApi,
  type ScoredFarmer,
} from './fixtures';
import type { APIRequestContext } from '@playwright/test';

test.describe('portfolio', () => {
  let api: APIRequestContext;
  let farmer: ScoredFarmer;

  test.beforeAll(async () => {
    api = await newApi();
    farmer = await createScoredFarmer(api, 'E2E Portfolio');
  });

  test.afterAll(async () => {
    await api.dispose();
  });

  test('finds the farmer and opens their case', async ({ page }) => {
    await page.goto('/');

    await expect(
      page.getByRole('heading', { level: 1, name: 'Hifadhi' }),
    ).toBeVisible();
    await expect(page.getByTestId('metric-farmers')).not.toHaveText('0');

    await page
      .getByRole('searchbox', { name: 'Search farmers' })
      .fill(farmer.fullName);

    const row = page.getByRole('link', { name: new RegExp(farmer.fullName) });
    await expect(row).toBeVisible();
    await row.click();

    await expect(page).toHaveURL(new RegExp(`/case/${farmer.id}$`));
    await expect(
      page.getByRole('navigation', { name: 'Case steps' }),
    ).toBeVisible();
  });
});
