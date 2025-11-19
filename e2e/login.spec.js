import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
    await page.goto('http://127.0.0.1:5000/login');
    await page.getByRole('textbox', { name: 'Username or Email' }).click();
    await page.getByRole('textbox', { name: 'Username or Email' }).fill('superadmin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).click();
    await page.getByRole('textbox', { name: 'Password' }).fill('ChangeMe123!');
    await page.getByRole('button', { name: 'Sign in' }).click();
});