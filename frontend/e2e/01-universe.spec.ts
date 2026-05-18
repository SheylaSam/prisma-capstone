import { test, expect } from "@playwright/test";

test("Universum mit 5 Ticker-Symbolen erstellen", async ({ page }) => {
  await page.goto("/universes");

  // Clear and fill the 5 ticker inputs (they are pre-filled)
  const tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"];
  for (let i = 0; i < 5; i++) {
    const input = page.getByTestId(`ticker-input-${i}`);
    await input.clear();
    await input.fill(tickers[i]);
  }

  // Set universe name
  await page.getByTestId("universe-name").fill("E2E Test Universum");

  // Submit form
  await page.getByTestId("create-universe-btn").click();

  // Should redirect to /rankings with universe_id in URL
  await expect(page).toHaveURL(/\/rankings\?universe_id=.+/, { timeout: 15_000 });
});
