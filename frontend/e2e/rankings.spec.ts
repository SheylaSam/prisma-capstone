import { test, expect } from '@playwright/test';

test.describe('PRISMA E2E', () => {
  test('1. Startseite lädt und zeigt Navigation', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/PRISMA|Dashboard/);
    await expect(page.getByRole('link', { name: /Universen/i })).toBeVisible();
  });

  test('2. Universe-Flow: neues Universum anlegen', async ({ page }) => {
    await page.goto('/universes');
    await page.getByRole('link', { name: /Neues Universum/i }).click();
    await expect(page).toHaveURL(/\/universes\/new/);

    const suffix = Date.now();
    await page.getByLabel('Name').fill(`e2e-flow-${suffix}`);
    await page.getByLabel('Region').fill('US');
    await page.getByLabel(/Ticker/i).fill('AAPL, MSFT');
    await page.getByRole('button', { name: /Universum anlegen/i }).click();

    await expect(page).toHaveURL(/\/universes$/);
    await expect(page.getByText(`e2e-flow-${suffix}`)).toBeVisible({ timeout: 10_000 });
  });
});
