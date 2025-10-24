
# core.py
# Core test logic: profiles, run, summary, CSV export, HTML report.
# Use only on systems you own or have explicit permission to test.

import requests, threading, time, csv, os, json
from collections import defaultdict
from datetime import datetime

def parse_profiles(text):
    profiles = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split('|')
        if len(parts) < 4:
            parts += [''] * (4 - len(parts))
        name, ua, ref, xff = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
        headers = {}
        if ua:
            headers['User-Agent'] = ua
        if ref:
            headers['Referer'] = ref
        if xff:
            headers['X-Forwarded-For'] = xff
        profiles.append((name or 'profile', headers))
    return profiles

def worker_thread(name, url, headers, reqs, timeout, allow_redirects, verify, result_list, proxy=None, stop_event=None):
    session = requests.Session()
    if proxy:
        session.proxies.update({'http': proxy, 'https': proxy})
    for i in range(reqs):
        if stop_event and stop_event.is_set():
            break
        start = time.time()
        try:
            resp = session.get(url, headers=headers, allow_redirects=allow_redirects, timeout=timeout, verify=verify)
            latency = (time.time() - start) * 1000.0
            result_list.append({
                'timestamp': datetime.utcnow().isoformat(),
                'profile': name,
                'attempt': i + 1,
                'status': resp.status_code,
                'reason': resp.reason,
                'latency_ms': round(latency, 2),
                'headers_sent': headers,
                'content_len': len(resp.content),
                'proxy': proxy
            })
        except Exception as e:
            latency = (time.time() - start) * 1000.0
            result_list.append({
                'timestamp': datetime.utcnow().isoformat(),
                'profile': name,
                'attempt': i + 1,
                'status': None,
                'reason': str(e),
                'latency_ms': round(latency, 2),
                'headers_sent': headers,
                'content_len': 0,
                'proxy': proxy
            })

def run_test(url, profiles, reqs_per_profile, threads_per_profile, timeout, allow_redirects, verify, proxies=None, stop_event=None):
    results = []
    threads = []
    proxy_count = len(proxies) if proxies else 0

    for name, headers in profiles:
        per_thread = max(1, reqs_per_profile // threads_per_profile)
        remainder = reqs_per_profile % threads_per_profile
        for t in range(threads_per_profile):
            count = per_thread + (1 if t < remainder else 0)
            if count <= 0:
                continue
            proxy = None
            if proxy_count > 0:
                proxy = proxies[t % proxy_count]
            thr = threading.Thread(
                target=worker_thread,
                args=(name, url, headers, count, timeout, allow_redirects, verify, results, proxy, stop_event),
                daemon=True
            )
            threads.append(thr)
            thr.start()

    for thr in threads:
        thr.join()

    return results

def summarize(results):
    total = len(results)
    per_profile = defaultdict(list)
    status_counts = defaultdict(int)
    latencies = []
    blocked = 0

    for r in results:
        per_profile[r['profile']].append(r)
        status_counts[r['status']] += 1
        if r['latency_ms'] is not None:
            latencies.append(r['latency_ms'])
        if r['status'] in (401, 403, 451):
            blocked += 1

    lines = []
    lines.append(f'Total attempts: {total}')
    for p, items in per_profile.items():
        succ = sum(1 for it in items if it['status'] and 200 <= it['status'] < 400)
        fail = len(items) - succ
        avg_lat = sum(it['latency_ms'] for it in items)/len(items) if items else 0
        lines.append(
            f"Profile '{p}': attempts={len(items)} success={succ} fail={fail} avg_latency_ms={avg_lat:.1f}"
        )

    lines.append(f'Status distribution: {dict(status_counts)}')

    if latencies:
        lat_sorted = sorted(latencies)
        def pick(percent):
            # simple percentile picker
            if not lat_sorted:
                return 0
            idx = int((percent/100.0) * (len(lat_sorted)-1))
            if idx < 0: idx = 0
            if idx > len(lat_sorted)-1: idx = len(lat_sorted)-1
            return lat_sorted[idx]

        avg_all = sum(latencies)/len(latencies)
        p50 = pick(50)
        p90 = pick(90)
        p99 = pick(99)

        lines.append(f'Avg latency overall: {avg_all:.1f} ms')
        lines.append(f'p50/p90/p99: {p50:.1f}/{p90:.1f}/{p99:.1f} ms')

    lines.append(f'Detected blocked responses (401/403/451): {blocked}')

    return "\n".join(lines)

def save_csv(results, path):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp','profile','attempt','status','reason',
            'latency_ms','content_len','proxy','headers_sent'
        ])
        for r in results:
            writer.writerow([
                r['timestamp'],
                r['profile'],
                r['attempt'],
                r['status'],
                r['reason'],
                r['latency_ms'],
                r['content_len'],
                r.get('proxy',''),
                json.dumps(r['headers_sent'])
            ])

def generate_html_report(results, path, meta=None):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    summary_text = summarize(results)

    rows_html = []
    for r in results:
        rows_html.append(
            '<tr>'
            f'<td>{r["timestamp"]}</td>'
            f'<td>{r["profile"]}</td>'
            f'<td>{r["attempt"]}</td>'
            f'<td>{r["status"]}</td>'
            f'<td>{r["reason"]}</td>'
            f'<td>{r["latency_ms"]}</td>'
            f'<td>{r.get("proxy","")}</td>'
            '</tr>'
        )
    table_html = """<table border="1" cellpadding="4" cellspacing="0">
<tr><th>timestamp</th><th>profile</th><th>attempt</th><th>status</th>
<th>reason</th><th>latency_ms</th><th>proxy</th></tr>
{rows}
</table>""".format(rows="\n".join(rows_html))

    html_doc = (
        '<!doctype html>\n'
        '<html><head><meta charset="utf-8">'
        '<title>Fake Sources Tester Report</title></head><body>'
        '<h1>Report</h1>'
        '<pre>{summary}</pre>'
        '{table}'
        '</body></html>'
    ).format(summary=summary_text, table=table_html)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html_doc)

    return path
