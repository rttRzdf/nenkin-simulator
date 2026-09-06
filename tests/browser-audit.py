"""Finite, reproducible browser audit. No storage or calculation mocks.
Run: python tests/browser-audit.py
Requires Playwright 1.57.0 and Chromium/WebKit/Firefox browser installations.
The live page is checked separately from the candidate repository build.
"""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import csv, hashlib, io, json, tempfile, traceback, urllib.request
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'qa-results'
OUT.mkdir(exist_ok=True)
LIVE = 'https://rttrzdf.github.io/nenkin-simulator/'
KEY = 'pension-life.v2'
checks, failures, observations = [], [], {}

def check(name, ok, details=None):
    checks.append({'name': name, 'pass': bool(ok), 'details': details})
    print(('PASS ' if ok else 'FAIL ') + name, flush=True)
    if not ok:
        failures.append(name)

def expand(page):
    page.locator('#stream-options').evaluate('(e) => e.open = true')

def export_settings(page):
    with page.expect_download() as event:
        page.locator('#export-json').click()
    return json.loads(Path(event.value.path()).read_text())

def case(page, typ, amount, extra=None):
    return page.evaluate('''([type, amount, extra]) => {
      const E = PensionCalc, c = E.clone(E.DEFAULTS);
      c.endAge = 65; c.tax.lagged = false;
      c.streams = [{...E.makeStream(type), amount, ...(extra || {})}];
      return E.simulate(c).rows[0];
    }''', [typ, amount, extra])

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / '_site')))
Thread(target=server.serve_forever, daemon=True).start()
LOCAL = f'http://127.0.0.1:{server.server_port}/'

try:
    req = urllib.request.Request(LIVE, headers={'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(req, timeout=30) as response:
        live_bytes = response.read()
        check('live HTTP 200 and HTML content', response.status == 200 and 'text/html' in response.headers.get('Content-Type', ''))
        observations['live_sha256'] = hashlib.sha256(live_bytes).hexdigest()
    observations['candidate_sha256'] = hashlib.sha256((ROOT / '_site/index.html').read_bytes()).hexdigest()
except Exception as exc:
    check('live HTTP retrieval', False, str(exc))

with sync_playwright() as p:
    for engine, mobile in [('chromium', False), ('webkit', False), ('webkit', True), ('firefox', False)]:
        label = engine + ('-mobile' if mobile else '-desktop')
        browser = None
        try:
            browser = getattr(p, engine).launch()
            observations[label + '-version'] = browser.version
            for target, url in [('live', LIVE), ('candidate', LOCAL)]:
                prefix = label + '/' + target
                options = dict(locale='ja-JP', timezone_id='Asia/Tokyo', accept_downloads=True, reduced_motion='reduce')
                if mobile:
                    options.update(p.devices['iPhone 13'])
                else:
                    options['viewport'] = {'width': 1440, 'height': 1000}
                context = browser.new_context(**options)
                page = context.new_page()
                page.set_default_timeout(10000)
                errors, network = [], []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('dialog', lambda dialog: dialog.accept())
                try:
                    response = page.goto(url, wait_until='networkidle')
                    check(prefix + ': real URL startup', response.ok and page.locator('#net-monthly').is_visible())
                    page.on('request', lambda request: network.append(request.url))
                    check(prefix + ': storage starts empty', page.evaluate('(key) => localStorage.getItem(key)', KEY) is None)
                    for typ in page.evaluate('Object.keys(PensionCalc.TYPES)'):
                        page.locator('#add-income').click()
                        page.locator('#stream-type').select_option(typ)
                        page.locator('#stream-amount').fill('300')
                        if typ == 'retirement':
                            page.locator('[name=serviceYears]').fill('11')
                        page.locator('#income-form [type=submit]').click()
                        expect(page.locator('#income-dialog')).not_to_be_visible()
                        page.locator('#income-list [data-edit]').click()
                        check(prefix + ': ' + typ + ' create/edit', page.locator('#stream-amount').input_value() == '300')
                        page.locator('#cancel-dialog').click()
                        page.locator('#income-list [data-remove]').click()
                        expect(page.locator('#income-list .income-row')).to_have_count(0)
                    page.locator('[data-new-type="salary"]').click()
                    page.locator('#stream-amount').fill('500')
                    page.locator('#income-form [type=submit]').click()
                    check(prefix + ': input alone does not auto-save', page.evaluate('(key) => localStorage.getItem(key)', KEY) is None)
                    settings = export_settings(page)
                    page.locator('#save-local').click()
                    expect(page.locator('#toast')).to_contain_text('保存しました')
                    check(prefix + ': actual localStorage bytes', page.evaluate('(key) => JSON.parse(localStorage.getItem(key))', KEY) == settings)
                    before = page.locator('#net-monthly').inner_text()
                    page.reload(wait_until='networkidle')
                    check(prefix + ': reload restores saved income', page.locator('#income-list .income-row').count() == 1 and page.locator('#net-monthly').inner_text() == before)
                    tab = context.new_page()
                    tab.goto(url, wait_until='networkidle')
                    check(prefix + ': new tab restores saved income', tab.locator('#income-list .income-row').count() == 1)
                    tab.close()
                    page.locator('#import-file').set_input_files({'name': 'bad.json', 'mimeType': 'application/json', 'buffer': b'{broken'})
                    expect(page.locator('#toast')).to_contain_text('読み込めません')
                    check(prefix + ': bad JSON preserves income', page.locator('#net-monthly').inner_text() == before)
                    page.locator('#clear-inputs').click()
                    page.locator('#import-file').set_input_files({'name': 'settings.json', 'mimeType': 'application/json', 'buffer': json.dumps(settings).encode()})
                    expect(page.locator('#toast')).to_contain_text('設定を読み込みました')
                    check(prefix + ': JSON round trip', export_settings(page) == settings)
                    with page.expect_download() as event:
                        page.locator('#export-csv').click()
                    csv_rows = list(csv.reader(io.StringIO(Path(event.value.path()).read_text(encoding='utf-8-sig'))))
                    check(prefix + ': CSV independently reconciles', len(csv_rows) == 32 and all(int(row[4]) - int(row[5]) - int(row[6]) - int(row[7]) - int(row[8]) == int(row[9]) and int(row[9]) + int(row[11]) - int(row[12]) == int(row[13]) for row in csv_rows[1:]))
                    page.locator('#end-age').fill('50')
                    check(prefix + ': invalid range hides stale results', page.locator('#errors').is_visible() and not page.locator('#result-content').is_visible() and page.locator('#export-csv').is_disabled())
                    page.locator('#end-age').fill('95')
                    check(prefix + ': correcting range restores results', not page.locator('#errors').is_visible())
                    for width in [320, 390, 768, 1440]:
                        page.set_viewport_size({'width': width, 'height': 844})
                        check(prefix + ': width ' + str(width), page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    page.set_viewport_size({'width': 390, 'height': 844})
                    page.locator('.mobile-results').click()
                    page.screenshot(path=str(OUT / (label + '-' + target + '.png')))
                    check(prefix + ': result reachable at mobile width', page.locator('#results').bounding_box()['y'] < 140)
                    page.emulate_media(media='print')
                    check(prefix + ': print CSS retains result', page.locator('#results').is_visible() and not page.locator('.settings').is_visible())
                    page.emulate_media(media='screen')
                    page.locator('#delete-saved').click()
                    check(prefix + ': deletion removes actual saved bytes', page.evaluate('(key) => localStorage.getItem(key)', KEY) is None)
                    page.reload(wait_until='networkidle')
                    check(prefix + ': deletion persists after reload', page.locator('#income-list .income-row').count() == 0)
                    care = case(page, 'salary', 1100000, {'insured': False, 'employment': False})['social']['care']
                    observations[prefix + ': salary110-care'] = care
                    if target == 'candidate':
                        check(prefix + ': Shinjuku official 1.1m salary care example', care == 87120, {'actual': care, 'expected': 87120})
                    check(prefix + ': no JS exceptions', not errors, errors)
                    # Navigation/reload requests are permitted; calculation must not contact other hosts.
                    check(prefix + ': no external calculation requests', all(item.startswith(url) or item.startswith('blob:') for item in network), network)
                except Exception as exc:
                    check(prefix + ': scenario completed', False, str(exc))
                    page.screenshot(path=str(OUT / (label + '-' + target + '-failure.png')))
                finally:
                    context.close()
            # Real browser-process restart with an on-disk browser profile. No set_storage_state mock.
            with tempfile.TemporaryDirectory() as profile:
                for first in [True, False]:
                    context = getattr(p, engine).launch_persistent_context(profile, accept_downloads=True)
                    page = context.new_page()
                    page.goto(LOCAL, wait_until='networkidle')
                    if first:
                        page.locator('[data-new-type="salary"]').click()
                        page.locator('#stream-amount').fill('500')
                        page.locator('#income-form [type=submit]').click()
                        page.locator('#save-local').click()
                        expect(page.locator('#toast')).to_contain_text('保存しました')
                    else:
                        check(label + ': real process restart persistence', page.locator('#income-list .income-row').count() == 1 and page.locator('#sample-badge').inner_text() == '端末の保存値')
                    context.close()
        except Exception as exc:
            check(label + ': browser execution', False, str(exc))
            traceback.print_exc()
        finally:
            if browser:
                browser.close()

server.shutdown()
report = {'checks': checks, 'failures': failures, 'observations': observations, 'passed': sum(x['pass'] for x in checks), 'total': len(checks), 'iphone_physical_device_tested': False}
(OUT / 'browser-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps({k: report[k] for k in ['passed', 'total', 'failures', 'observations']}, ensure_ascii=False, indent=2))
raise SystemExit(1 if failures else 0)
