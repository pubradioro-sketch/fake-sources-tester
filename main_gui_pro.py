
#!/usr/bin/env python3
'''main_gui_pro.py - GUI Pro version.
Use only on systems you own / have permission to test.
Shows progress bar, live metrics, histogram, request log, CSV + HTML export, presets, URL validation.
'''

import PySimpleGUI as sg
import threading, time, os, json
from core import parse_profiles, run_test, summarize, save_csv, generate_html_report

sg.theme('LightBlue')

PRESETS_FILE = 'presets.json'

DEFAULT_PRESETS = {
    'Default': [
        'Chrome_Windows|Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/...|https://google.com/|203.0.113.10',
        'Mobile_Safari|Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) Safari/604.1|https://m.facebook.com/|192.0.2.45',
        'Bot_Simple|curl/7.88.1||203.0.113.77'
    ]
}

def load_presets():
    if os.path.exists(PRESETS_FILE):
        try:
            with open(PRESETS_FILE,'r',encoding='utf-8') as f:
                return json.load(f)
        except:
            return DEFAULT_PRESETS
    return DEFAULT_PRESETS

def save_presets(presets):
    with open(PRESETS_FILE,'w',encoding='utf-8') as f:
        json.dump(presets, f, indent=2)

def validate_url(u):
    if not u:
        return False, 'Empty'
    if not (u.startswith('http://') or u.startswith('https://')):
        return False, 'Must start with http:// or https://'
    return True, 'OK'

def build_histogram(latencies, bins=8):
    if not latencies:
        return 'No data'
    mn = min(latencies); mx = max(latencies)
    if mn == mx:
        return f'All latencies: {mn:.1f} ms'
    span = (mx - mn) if (mx - mn) > 0 else 1
    width = span / bins
    counts = [0]*bins
    for v in latencies:
        idx = int((v-mn)/width)
        if idx == bins:
            idx = bins-1
        counts[idx]+=1
    out_lines = []
    total = len(latencies)
    for i,c in enumerate(counts):
        low = mn + i*width
        high = low + width
        bar = '█'*(c*40//total) if total>0 else ''
        out_lines.append(f'{low:.0f}-{high:.0f} ms |{bar} ({c})')
    return '\n'.join(out_lines)

presets = load_presets()

layout = [
    [sg.Text('Target URL:'), sg.Input(key='-URL-', size=(70,1)), sg.Text('', key='-URLVAL-')],
    [sg.Text('Requests/profile'), sg.Input('10', key='-REQS-', size=(6,1)),
     sg.Text('Threads/profile'), sg.Input('2', key='-THREADS-', size=(6,1)),
     sg.Text('Timeout(s)'), sg.Input('10', key='-TOUT-', size=(6,1)),
     sg.Checkbox('Verify TLS', key='-VERIFY-', default=True),
     sg.Checkbox('Allow redirects', key='-REDIR-', default=True)],
    [sg.Text('Proxies file'), sg.Input(key='-PROXFILE-', size=(50,1)), sg.FileBrowse()],
    [sg.Text('Profiles'), sg.Combo(list(presets.keys()), key='-PRESETS-', enable_events=True),
     sg.Button('Load Preset'), sg.Button('Save Preset'), sg.Button('Add Preset')],
    [sg.Multiline('\n'.join(presets.get('Default',[])), key='-PROFILES-', size=(100,8))],
    [sg.Button('Start Test', key='-START-'),
     sg.Button('Stop', key='-STOP-', disabled=True),
     sg.Button('Save CSV', key='-SAVE-', disabled=True),
     sg.Button('Export HTML', key='-HTML-', disabled=True)],
    [sg.Text('Progress:'), sg.Text('Idle', key='-PROG-'),
     sg.ProgressBar(100, orientation='h', size=(40,20), key='-PB-')],
    [sg.Frame('Live Metrics', [[sg.Multiline('', size=(70,10), key='-METRICS-', disabled=True)]),
              sg.Frame('Latency Histogram', [[sg.Multiline('', size=(40,10), key='-HIST-', disabled=True)]])],
    [sg.Frame('Request Log (tail 200)', [[sg.Multiline('', size=(120,8), key='-LOG-', disabled=True)]])],
    [sg.Text('Legal: Use only on property you own or have permission to test.')]
]

window = sg.Window('Fake Sources Tester Pro', layout, finalize=True, resizable=True)

stop_event = threading.Event()
results = []
total_expected = 0

def updater_thread():
    # Updates UI periodically with progress and live metrics.
    while not stop_event.is_set():
        time.sleep(0.5)
        sent = len(results)
        pct = int((sent/total_expected)*100) if total_expected>0 else 0
        window.write_event_value('-UPD-', {'sent': sent, 'pct': pct})

def run_worker(url, profiles, reqs, threads, tout, allow_redirects, verify, proxies):
    global results
    results = []
    res = run_test(url, profiles, reqs, threads, tout, allow_redirects, verify, proxies=proxies, stop_event=stop_event)
    window.write_event_value('-DONE-', res)

while True:
    event, values = window.read(timeout=200)
    if event == sg.WIN_CLOSED:
        break

    if event == '-PRESETS-':
        pass

    if event == 'Load Preset':
        key = values['-PRESETS-']
        if key in presets:
            window['-PROFILES-'].update('\n'.join(presets[key]))

    if event == 'Save Preset':
        name = sg.popup_get_text('Preset name:')
        if name:
            presets[name] = [line for line in values['-PROFILES-'].splitlines() if line.strip()]
            save_presets(presets)
            window['-PRESETS-'].update(values=list(presets.keys()))
            sg.popup('Saved')

    if event == 'Add Preset':
        name = sg.popup_get_text('New preset name:')
        if name:
            presets[name] = [line for line in values['-PROFILES-'].splitlines() if line.strip()]
            save_presets(presets)
            window['-PRESETS-'].update(values=list(presets.keys()))
            sg.popup('Added')

    if event == '-START-':
        url = values['-URL-'].strip()
        ok,msg = validate_url(url)
        if not ok:
            sg.popup_error(f'Invalid URL: {msg}')
            continue

        try:
            reqs = int(values['-REQS-'])
            threads = int(values['-THREADS-'])
            tout = float(values['-TOUT-'])
        except:
            sg.popup_error('Invalid numeric parameters')
            continue

        proxies = []
        if values['-PROXFILE-']:
            try:
                with open(values['-PROXFILE-'],'r',encoding='utf-8') as f:
                    proxies = [l.strip() for l in f.readlines() if l.strip()]
            except Exception as e:
                sg.popup_error('Cannot read proxies file:', str(e))
                continue

        profiles = parse_profiles(values['-PROFILES-'])
        total_expected = reqs * len(profiles)

        stop_event.clear()
        window['-START-'].update(disabled=True)
        window['-STOP-'].update(disabled=False)
        window['-PROG-'].update('Running...')
        window['-PB-'].update(0)

        updater = threading.Thread(target=updater_thread, daemon=True)
        updater.start()

        thr = threading.Thread(
            target=run_worker,
            args=(url, profiles, reqs, threads, tout,
                  values['-REDIR-'], values['-VERIFY-'], proxies),
            daemon=True
        )
        thr.start()

    if event == '-STOP-':
        stop_event.set()
        window['-START-'].update(disabled=False)
        window['-STOP-'].update(disabled=True)

    if event == '-UPD-':
        data = values['-UPD-']
        sent = data['sent']
        pct = data['pct']
        window['-PB-'].update(pct)
        window['-PROG-'].update(f'{sent} / {total_expected} requests ({pct}%)')

        # live metrics
        s = summarize(results)
        window['-METRICS-'].update(s)

        # live histogram
        lats = [r['latency_ms'] for r in results if r['latency_ms'] is not None]
        window['-HIST-'].update(build_histogram(lats))

        # live tail log
        tail = '\n'.join([
            f'[{r.get("status")}] {r.get("latency_ms")}ms {r.get("profile")} proxy={r.get("proxy","")}' 
            for r in results[-200:]
        ])
        window['-LOG-'].update(tail)

    if event == '-DONE-':
        res = values['-DONE-']
        results = res
        window['-PROG-'].update('Finished')
        window['-PB-'].update(100)
        window['-SAVE-'].update(disabled=False)
        window['-HTML-'].update(disabled=False)
        window['-START-'].update(disabled=False)
        window['-STOP-'].update(disabled=True)

        final_summary = summarize(results)
        window['-METRICS-'].update(final_summary)

        lats = [r['latency_ms'] for r in results if r['latency_ms'] is not None]
        window['-HIST-'].update(build_histogram(lats))

        tail = '\n'.join([
            f'[{r.get("status")}] {r.get("latency_ms")}ms {r.get("profile")} proxy={r.get("proxy","")}' 
            for r in results[-200:]
        ])
        window['-LOG-'].update(tail)

    if event == '-SAVE-':
        if not results:
            sg.popup('No results')
        else:
            fn = sg.popup_get_file('Save CSV', save_as=True, default_extension='csv', file_types=(('CSV','*.csv'),))
            if fn:
                save_csv(results, fn)
                sg.popup('Saved:', fn)

    if event == '-HTML-':
        if not results:
            sg.popup('No results')
        else:
            fn = sg.popup_get_file('Save HTML report', save_as=True, default_extension='html', file_types=(('HTML','*.html'),))
            if fn:
                generate_html_report(results, fn)
                sg.popup('Saved HTML report:', fn)

window.close()
