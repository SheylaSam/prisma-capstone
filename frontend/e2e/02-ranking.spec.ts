import { test, expect } from "@playwright/test";

test("Ranking-Lauf starten und Tabelle mit 5 Zeilen anzeigen", async ({ page, request }) => {
  const apiBase = process.env.PLAYWRIGHT_API_URL ?? "http://localhost:8000";

  // Setup: create universe via API
  const universeResp = await request.post(`${apiBase}/api/v1/universes`, {
    data: {
      name: "E2E Ranking Test",
      region: "US",
      tickers: ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
    },
  });
  expect(universeResp.ok()).toBeTruthy();
  const universe = await universeResp.json();

  await page.goto(`/rankings?universe_id=${universe.id}`);

  // Click "Ranking starten"
  await page.getByTestId("start-ranking-btn").click();

  // Wait for table to appear
  const table = page.getByTestId("rankings-table");
  await expect(table).toBeVisible({ timeout: 30_000 });

  // Verify exactly 5 rows in tbody
  const rows = table.locator("tbody tr");
  await expect(rows).toHaveCount(5);
});
