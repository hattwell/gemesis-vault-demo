import { expect, test } from "@playwright/test";

test("fictional catalogue, search, references and scripted chat work without external links", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("note")).toContainText("Демо · вымышленные данные");
  const nav = page.getByRole("navigation", { name: "Разделы Vault" });
  await nav.getByRole("button", { name: "Каталог" }).click();
  await expect(page.locator(".card-open")).toHaveCount(20);
  await page.getByRole("textbox", { name: "Поиск по каталогу" }).fill("Сигналяр");
  await expect(page.locator(".card-open")).toHaveCount(1);
  await page.getByRole("textbox", { name: "Поиск по каталогу" }).clear();
  await page.locator(".card-open").first().click();
  await expect(page.locator(".detail")).toContainText("вымышленный пример");
  await expect(page.locator(".detail a[href*='.example']")).toHaveCount(0);
  await page.getByRole("button", { name: "Демо-чат" }).click();
  await page.getByRole("button", { name: "Аэролит", exact: true }).click();
  await expect(page.locator(".chat .log")).toContainText("Сценарный ответ:");
  const bounds = await page.locator(".chat").boundingBox();
  const width = page.viewportSize()!.width;
  expect(bounds).not.toBeNull();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
  expect(errors).toEqual([]);
});

test("MCP setup describes only public read-only access", async ({ page, request }) => {
  await page.goto("/");
  await page.getByRole("navigation", { name: "Разделы Vault" }).getByRole("button", { name: "MCP" }).click();
  await expect(page.getByRole("heading", { name: "Попробуйте Gemesis через MCP" })).toBeVisible();
  await expect(page.locator(".mcp-tools li")).toHaveCount(5);
  await expect(page.locator(".mcp-page input")).toHaveCount(0);
  await expect(page.getByText("demo-readonly").first()).toBeVisible();
  await expect.poll(async () => (await request.get("/admin")).status()).toBe(404);
  await expect.poll(async () => (await request.post("/api/chat/feedback", { data: {} })).status()).toBe(404);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  expect(overflow).toBe(false);
});
