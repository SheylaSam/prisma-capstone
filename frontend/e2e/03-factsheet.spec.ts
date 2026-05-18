import { test, expect } from "@playwright/test";

test("Auf Aktie klicken und Factsheet mit Kennzahlen öffnen", async ({ page, request }) => {
  const apiBase = process.env.PLAYWRIGHT_API_URL ?? "http://localhost:8000";

  // Setup: universe + run via API
  const universeResp = await request.post(`${apiBase}/api/v1/universes`, {
    data: { name: "E2E Factsheet", tickers: ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"] },
  });
  const universe = await universeResp.json();

  await page.goto(`/rankings?universe_id=${universe.id}`);
  await page.getByTestId("start-ranking-btn").click();

  const table = page.getByTestId("rankings-table");
  await expect(table).toBeVisible({ timeout: 30_000 });

  // Click on first stock row
  const firstRow = table.locator("tbody tr").first();
  const ticker = (await firstRow.locator("td:nth-child(2)").textContent())?.trim();
  await firstRow.click();

  // Should navigate to factsheet
  await expect(page).toHaveURL(new RegExp(`/stocks/${ticker}`), { timeout: 10_000 });

  // Factsheet should show ticker and metrics section
  await expect(page.getByTestId("factsheet-ticker")).toBeVisible();
  await expect(page.getByTestId("factsheet-metrics")).toBeVisible();
  await expect(page.getByTestId("request-memo-btn")).toBeVisible();
});
