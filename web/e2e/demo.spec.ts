import { test, expect, type Page } from '@playwright/test';
import { readFileSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

const credentials: {role: string; email: string; password: string}[] = JSON.parse(readFileSync(resolve('../runtime/demo-credentials.json'), 'utf-8'));
const screenshots = resolve(process.env.SCREENSHOT_DIR || '../presentation/screenshots');
mkdirSync(screenshots, { recursive: true });

async function login(page: Page, role: string) {
  const user = credentials.find(c => c.role === role)!;
  await page.goto('/');
  await page.getByLabel('Email address or mobile number').fill(user.email);
  await page.getByLabel('Password', { exact: true }).fill(user.password);
  await page.getByRole('button', { name: 'Sign in →', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'A greener Nellai starts with us.' })).toBeVisible();
}

test('citizen report → authority resolution → citizen verification', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  await login(page, 'CITIZEN');
  await page.getByRole('button', { name: 'Report an issue', exact: true }).last().click();
  await page.getByLabel('Issue title').fill('Browser test: drain maintenance demonstration');
  await page.getByRole('combobox', { name: 'Category', exact: true }).selectOption('DRAIN_BLOCKAGE');
  await page.getByLabel('Locality', { exact: true }).fill('Palayamkottai');
  await page.getByLabel('Description', { exact: true }).fill('DEMONSTRATION TEST: A drainage maintenance report created by the browser verification suite.');
  await page.locator('input[name="photo"]').setInputFiles(resolve('../tests/fixtures/evidence.png'));
  await page.getByLabel('Latitude', { exact: true }).fill('8.7200');
  await page.getByLabel('Longitude', { exact: true }).fill('77.7410');
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Submit issue', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Browser test: drain maintenance demonstration' })).toBeVisible();
  const complaintUrl = page.url();
  await expect(page.getByText('Demo civic response team', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();

  await login(page, 'AUTHORITY');
  await page.goto(complaintUrl);
  await page.getByRole('button', { name: 'Acknowledge report', exact: true }).click();
  await page.getByLabel('Reason for this update').fill('Demo authority has accepted this work order.');
  await page.getByRole('button', { name: 'Save update', exact: true }).click();
  await page.getByRole('button', { name: 'Start work', exact: true }).click();
  await page.getByLabel('Reason for this update').fill('Demo maintenance team has started cleaning.');
  await page.getByRole('button', { name: 'Save update', exact: true }).click();
  await page.getByRole('button', { name: 'Submit resolution', exact: true }).click();
  await page.getByLabel('What work was completed?').fill('DEMONSTRATION TEST: Obstruction removed and the drain has been cleared.');
  await page.locator('input[name="photo"]').setInputFiles(resolve('../tests/fixtures/evidence.png'));
  await page.getByRole('button', { name: 'Save update', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Resolution evidence', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();

  await login(page, 'CITIZEN');
  await page.goto(complaintUrl);
  await page.getByRole('button', { name: 'Verify the resolution', exact: true }).click();
  await page.getByRole('combobox', { name: 'Is the issue resolved?', exact: true }).selectOption('yes');
  await page.getByLabel('Feedback / reason').fill('I confirm the demonstration issue is resolved.');
  await page.getByRole('button', { name: 'Submit verification', exact: true }).click();
  await expect(page.getByText('Resolution verified by the citizen.', { exact: true })).toBeVisible();
  await page.screenshot({ path: resolve(screenshots, 'complaint-workflow.png'), fullPage: true });
  expect(errors).toEqual([]);
});

test('admin dashboard, modules, environmental pages and responsive layout', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  await login(page, 'SUPER_ADMIN');
  await expect(page.locator('.metric strong').first()).not.toHaveText('—');
  await expect(page.locator('.leaflet-container')).toBeVisible();
  await expect(page.locator('.leaflet-marker-icon').first()).toBeVisible();
  await page.screenshot({ path: resolve(screenshots, 'dashboard.png'), fullPage: true, animations: 'disabled' });
  for (const [nav, title, file] of [
    ['Green Nellai', 'Plant a tree. Nurture a future.', 'trees'],
    ['Volunteer Nellai', 'Good things grow when we come together.', 'volunteers'],
    ['Neervalam', 'Care for the water that connects us.', 'water'],
    ['Administration', 'Configure responsibility. Keep it accountable.', 'administration'],
    ['Module registry', 'One platform. Room to grow.', 'modules'],
  ]) {
    await page.getByRole('button', { name: nav, exact: true }).click();
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
    await page.screenshot({ path: resolve(screenshots, `${file}.png`), fullPage: true });
  }
  await page.getByRole('button', { name: 'Overview', exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('button', { name: 'Open navigation' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: resolve(screenshots, 'mobile-web.png'), fullPage: true });
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.getByRole('button', { name: 'Civic reports', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Every issue deserves a response.' })).toBeVisible();
  expect(errors).toEqual([]);
});

test('authority email outbox shows the real queued demo complaint', async ({ page }) => {
  const complaint: {reference: string; title: string} = JSON.parse(readFileSync(resolve('../runtime/complaint-email-test.json'), 'utf-8'));
  await login(page, 'SUPER_ADMIN');
  await page.getByRole('button', { name: 'Authority email outbox', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Every report reaches the outbox.' })).toBeVisible();
  await page.locator('.email-item').filter({ hasText: complaint.reference }).click();
  const preview = page.getByRole('region', { name: 'Email preview' });
  await expect(preview.getByRole('heading', { name: `New complaint: ${complaint.reference}` })).toBeVisible();
  await expect(preview.getByText('sandymuthukutti@gmail.com', { exact: true })).toBeVisible();
  await expect(preview.locator('.email-body')).toContainText('TEST ONLY');
  await page.screenshot({ path: resolve(screenshots, 'email-outbox.png'), fullPage: true, animations: 'disabled' });
  await preview.getByRole('button', { name: 'Open complaint' }).click();
  await expect(page.getByRole('heading', { name: complaint.title })).toBeVisible();
  // Links from an authority email must survive a fresh sign-in.
  const reportUrl = page.url();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.goto(reportUrl);
  const admin = credentials.find(c => c.role === 'SUPER_ADMIN')!;
  await page.getByLabel('Email address or mobile number').fill(admin.email);
  await page.getByLabel('Password', { exact: true }).fill(admin.password);
  await page.getByRole('button', { name: 'Sign in →', exact: true }).click();
  await expect(page.getByRole('heading', { name: complaint.title })).toBeVisible();
});
