"""Browser smoke test for an explicitly provisioned throwaway technician account.

UI_BASE_URL defaults to http://127.0.0.1:5173. Credentials are environment-only.
Optional CHROMIUM_EXECUTABLE supports a separately installed test browser.
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    username=os.environ['UI_TEST_USERNAME']
    password=os.environ['UI_TEST_PASSWORD']
    output=Path(os.getenv('UI_SCREENSHOT_DIR','test-results'))
    output.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        options={'headless':True}
        if os.getenv('CHROMIUM_EXECUTABLE'):
            options.update(executable_path=os.environ['CHROMIUM_EXECUTABLE'],args=['--no-sandbox','--no-zygote','--single-process','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--in-process-gpu'])
        browser=p.chromium.launch(**options)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(os.getenv('UI_BASE_URL','http://127.0.0.1:5173'))
        expect(page.get_by_role('heading',name='Welcome to the garage.')).to_be_visible()
        page.screenshot(path=str(output/'login.png'),full_page=True)
        page.get_by_label('Username or email').fill(username)
        page.get_by_label('Password',exact=True).fill('incorrect test password')
        page.get_by_role('button',name='Sign in',exact=True).click()
        expect(page.get_by_role('alert')).to_contain_text('Incorrect username or password')
        page.get_by_label('Password',exact=True).fill(password)
        page.get_by_role('button',name='Sign in',exact=True).click()
        expect(page.get_by_role('heading',name='Vehicle overview')).to_be_visible()
        page.get_by_role('button',name='Settings',exact=True).click()
        page.get_by_label('Motor temperature warning').focus()
        page.get_by_label('Motor temperature warning').press('Home')
        page.get_by_role('button',name='Save settings').click()
        expect(page.get_by_role('status')).to_contain_text('saved')
        page.reload()
        page.get_by_role('button',name='Settings',exact=True).click()
        expect(page.get_by_label('Motor temperature warning')).to_have_value('40')
        page.get_by_role('button',name='Live telemetry',exact=True).click()
        page.get_by_label('Simulation time').focus()
        page.get_by_label('Simulation time').press('End')
        expect(page.get_by_text('High motor temperature',exact=True)).to_be_visible()
        page.screenshot(path=str(output/'live.png'),full_page=True)
        page.get_by_role('button',name='Sessions',exact=True).click()
        page.get_by_role('button',name='View diagnostics').first.click()
        expect(page.get_by_role('heading',name='Performance analysis')).to_be_visible()
        expect(page.locator('.recharts-wrapper')).to_have_count(5)
        page.screenshot(path=str(output/'diagnostics.png'),full_page=True)
        page.get_by_role('button',name='Backups',exact=True).click()
        expect(page.get_by_role('heading',name='Database backups')).to_be_visible()
        page.set_viewport_size({'width':390,'height':844})
        expect(page.get_by_role('button',name='Sign out')).to_be_visible()
        page.get_by_role('button',name='Sign out').click()
        expect(page.get_by_role('heading',name='Welcome to the garage.')).to_be_visible()
        assert page.request.get(os.getenv('UI_BASE_URL','http://127.0.0.1:5173')+'/api/live').status==401
        assert not errors,errors
        browser.close()
    print('Browser checks passed: login rejection/success, saved settings, warnings, five charts, responsive navigation, logout/access denial.')

if __name__=='__main__':main()
