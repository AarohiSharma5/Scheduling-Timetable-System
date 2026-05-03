#include <algorithm>
#include <arpa/inet.h>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <netinet/in.h>
#include <numeric>
#include <queue>
#include <sstream>
#include <string>
#include <sys/socket.h>
#include <unistd.h>
#include <vector>
#include <thread>

using namespace std;

#define fastio ios_base::sync_with_stdio(false); cin.tie(NULL)
#define pb push_back
#define all(x) (x).begin(), (x).end()
#define sz(x) (int)((x).size())
#define rep(i,a,b) for (int i = (a); i < (b); ++i)
#define pii pair<int,int>
#define vi vector<int>

const string RESET = "\033[0m";
const string BOLD = "\033[1m";
const string RED = "\033[31m";
const string GREEN = "\033[32m";
const string YELLOW = "\033[33m";
const string BLUE = "\033[34m";
const string CYAN = "\033[36m";
const string MAGENTA = "\033[35m";

struct Activity {
    int id, name_id, start, finish, weight, deadline;
};

struct AnalyticsResult {
    int totalActivities;
    int selectedActivities;
    int totalWeight;
    double utilizationPercent;
    int idleTimeMinutes;
    int timeSlotCoverage;
};

struct ConflictReport {
    vector<pii> conflictPairs;
    int totalConflicts;
    bool hasConflicts;
};

class DSU {
public:
    vi parent;
    DSU(int n) : parent(n + 1) {
        iota(all(parent), 0);
    }
    int find(int x) {
        return parent[x] == x ? x : parent[x] = find(parent[x]);
    }
    void unite(int u, int v) {
        parent[find(u)] = find(v);
    }
};

thread_local map<int, string> activityNames;

int timeToMinutes(const string& t) {
    int h = 0, m = 0;
    int matched = sscanf(t.c_str(), "%d:%d", &h, &m);
    if (matched != 2) return -1;
    if (h < 0 || h > 23 || m < 0 || m > 59) return -1;
    return h * 60 + m;
}

string minutesToTime(int mins) {
    int h = mins / 60;
    int m = mins % 60;
    char buf[16];
    snprintf(buf, sizeof(buf), "%02d:%02d", h, m);
    return string(buf);
}

string trim(const string& s) {
    size_t start = s.find_first_not_of(" \t\r\n");
    if (start == string::npos) return "";
    size_t end = s.find_last_not_of(" \t\r\n");
    return s.substr(start, end - start + 1);
}

string htmlEscape(const string& s) {
    string out;
    out.reserve(s.size());
    for (char c : s) {
        switch (c) {
            case '&': out += "&amp;"; break;
            case '<': out += "&lt;"; break;
            case '>': out += "&gt;"; break;
            case '"': out += "&quot;"; break;
            case '\'': out += "&#39;"; break;
            default: out += c; break;
        }
    }
    return out;
}

string urlDecode(const string& input) {
    string out;
    out.reserve(input.size());
    for (size_t i = 0; i < input.size(); ++i) {
        char c = input[i];
        if (c == '+') {
            out += ' ';
        } else if (c == '%' && i + 2 < input.size()) {
            string hex = input.substr(i + 1, 2);
            char decoded = static_cast<char>(strtol(hex.c_str(), nullptr, 16));
            out += decoded;
            i += 2;
        } else {
            out += c;
        }
    }
    return out;
}

map<string, string> parseFormUrlEncoded(const string& body) {
    map<string, string> values;
    size_t pos = 0;
    while (pos < body.size()) {
        size_t amp = body.find('&', pos);
        if (amp == string::npos) amp = body.size();
        string pairText = body.substr(pos, amp - pos);
        size_t eq = pairText.find('=');
        string key = urlDecode(pairText.substr(0, eq));
        string value = eq == string::npos ? "" : urlDecode(pairText.substr(eq + 1));
        values[key] = value;
        pos = amp + 1;
    }
    return values;
}

string sampleActivitiesText() {
    return
        "Math,09:00,10:00,5,12:00\n"
        "Physics,10:00,11:30,4,12:00\n"
        "Chemistry,09:30,11:00,3,11:00\n"
        "CS-Lab,11:00,13:00,5,14:00\n"
        "English,11:30,12:30,2,13:00\n"
        "DSA,13:00,14:30,5,15:00\n"
        "Sports,14:00,15:00,1,16:00\n"
        "Library,15:00,16:30,3,17:00\n"
        "Workshop,16:00,18:00,4,18:00\n"
        "Seminar,14:30,16:00,4,16:00";
}

vector<Activity> parseActivitiesFromText(const string& text, vector<string>& errors) {
    activityNames.clear();
    vector<Activity> acts;
    istringstream input(text);
    string line;
    int lineNumber = 0;

    while (getline(input, line)) {
        ++lineNumber;
        line = trim(line);
        if (line.empty()) continue;

        // parse CSV line allowing quoted fields
        vector<string> parts;
        string cur;
        bool inQuotes = false;
        for (size_t i = 0; i < line.size(); ++i) {
            char c = line[i];
            if (c == '"') {
                if (inQuotes && i + 1 < line.size() && line[i+1] == '"') { // escaped quote
                    cur += '"';
                    ++i;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (c == ',' && !inQuotes) {
                parts.pb(trim(cur));
                cur.clear();
            } else {
                cur += c;
            }
        }
        parts.pb(trim(cur));
        for (auto &p : parts) {
            if (p.size() >= 2 && p.front() == '"' && p.back() == '"') p = p.substr(1, p.size()-2);
        }

        if (parts.size() != 5) {
            errors.pb("Line " + to_string(lineNumber) + ": expected 5 comma-separated fields.");
            continue;
        }

        try {
            int id = sz(acts) + 1;
            string name = parts[0];
            int start = timeToMinutes(parts[1]);
            int finish = timeToMinutes(parts[2]);
            int weight = stoi(parts[3]);
            int deadlineMin = timeToMinutes(parts[4]);
            if (start < 0 || finish < 0) {
                errors.pb("Line " + to_string(lineNumber) + ": invalid start/finish time format (use HH:MM).");
                continue;
            }
            if (deadlineMin < 0) {
                errors.pb("Line " + to_string(lineNumber) + ": invalid deadline time format (use HH:MM).");
                continue;
            }
            int deadline = deadlineMin / 60;

            if (finish <= start) {
                errors.pb("Line " + to_string(lineNumber) + ": finish time must be after start time.");
                continue;
            }
            if (weight < 1 || weight > 10) {
                errors.pb("Line " + to_string(lineNumber) + ": priority must be between 1 and 10.");
                continue;
            }

            activityNames[id] = name;
            acts.pb({id, id, start, finish, weight, deadline});
        } catch (...) {
            errors.pb("Line " + to_string(lineNumber) + ": invalid activity data.");
        }
    }

    const int MAX_ACTIVITIES = 1000;
    if ((int)acts.size() > MAX_ACTIVITIES) {
        errors.pb("Too many activities provided (max " + to_string(MAX_ACTIVITIES) + "). Truncated.");
        acts.resize(MAX_ACTIVITIES);
    }

    return acts;
}

vector<Activity> activitySelection(vector<Activity> acts) {
    sort(all(acts), [](const Activity& a, const Activity& b) {
        return a.finish < b.finish;
    });

    vector<Activity> selected;
    int lastFinish = -1;
    rep(i, 0, sz(acts)) {
        if (acts[i].start >= lastFinish) {
            selected.pb(acts[i]);
            lastFinish = acts[i].finish;
        }
    }
    return selected;
}

vector<Activity> weightedScheduling(vector<Activity> acts) {
    sort(all(acts), [](const Activity& a, const Activity& b) {
        if (a.weight != b.weight) return a.weight > b.weight;
        return a.finish < b.finish;
    });

    vector<Activity> selected;
    rep(i, 0, sz(acts)) {
        bool conflict = false;
        rep(j, 0, sz(selected)) {
            if (max(acts[i].start, selected[j].start) < min(acts[i].finish, selected[j].finish)) {
                conflict = true;
                break;
            }
        }
        if (!conflict) selected.pb(acts[i]);
    }

    sort(all(selected), [](const Activity& a, const Activity& b) {
        return a.start < b.start;
    });
    return selected;
}

vector<Activity> jobSequencingDSU(vector<Activity> jobs) {
    if (sz(jobs) == 0) return {};

    sort(all(jobs), [](const Activity& a, const Activity& b) {
        return a.weight > b.weight;
    });

    int maxDl = 0;
    rep(i, 0, sz(jobs)) maxDl = max(maxDl, jobs[i].deadline);

    DSU dsu(maxDl);
    vector<Activity> result(maxDl + 1);
    vector<bool> filled(maxDl + 1, false);

    rep(i, 0, sz(jobs)) {
        int slot = dsu.find(jobs[i].deadline);
        if (slot > 0) {
            result[slot] = jobs[i];
            filled[slot] = true;
            dsu.unite(slot, slot - 1);
        }
    }

    vector<Activity> scheduled;
    rep(i, 1, maxDl + 1) {
        if (filled[i]) scheduled.pb(result[i]);
    }
    return scheduled;
}

int minRoomsRequired(vector<Activity> acts, vector<vector<Activity>>& rooms) {
    sort(all(acts), [](const Activity& a, const Activity& b) {
        return a.start < b.start;
    });

    priority_queue<pii, vector<pii>, greater<pii>> pq;
    int roomCount = 0;
    rooms.clear();

    rep(i, 0, sz(acts)) {
        if (!pq.empty() && pq.top().first <= acts[i].start) {
            int rid = pq.top().second;
            pq.pop();
            rooms[rid].pb(acts[i]);
            pq.push({acts[i].finish, rid});
        } else {
            rooms.pb({{acts[i]}});
            pq.push({acts[i].finish, roomCount});
            roomCount++;
        }
    }
    return roomCount;
}

vector<Activity> weightedIntervalSchedulingDP(vector<Activity> acts) {
    if (sz(acts) == 0) return {};

    sort(all(acts), [](const Activity& a, const Activity& b) {
        return a.finish < b.finish;
    });

    int n = sz(acts);
    vi dp(n);
    vi parent_idx(n, -1);

    auto findLatest = [&](int idx) {
        int lo = 0, hi = idx - 1;
        int res = -1;
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            if (acts[mid].finish <= acts[idx].start) {
                res = mid;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        return res;
    };

    dp[0] = acts[0].weight;
    rep(i, 1, n) {
        int inclWeight = acts[i].weight;
        int latest = findLatest(i);
        if (latest != -1) inclWeight += dp[latest];
        if (inclWeight > dp[i - 1]) {
            dp[i] = inclWeight;
            parent_idx[i] = latest;
        } else {
            dp[i] = dp[i - 1];
            parent_idx[i] = -2;
        }
    }

    vector<Activity> selected;
    int idx = n - 1;
    while (idx >= 0) {
        if (parent_idx[idx] != -2) {
            selected.pb(acts[idx]);
            idx = parent_idx[idx];
        } else {
            idx--;
        }
    }

    reverse(all(selected));
    return selected;
}

ConflictReport detectConflicts(const vector<Activity>& acts) {
    ConflictReport report;
    report.totalConflicts = 0;
    report.hasConflicts = false;

    rep(i, 0, sz(acts)) {
        rep(j, i + 1, sz(acts)) {
            if (max(acts[i].start, acts[j].start) < min(acts[i].finish, acts[j].finish)) {
                report.conflictPairs.pb({acts[i].id, acts[j].id});
                report.totalConflicts++;
                report.hasConflicts = true;
            }
        }
    }
    return report;
}

AnalyticsResult computeAnalytics(const vector<Activity>& allActs, const vector<Activity>& selected) {
    AnalyticsResult res;
    res.totalActivities = sz(allActs);
    res.selectedActivities = sz(selected);
    res.totalWeight = 0;

    int minTime = INT_MAX, maxTime = 0;
    rep(i, 0, sz(selected)) {
        res.totalWeight += selected[i].weight;
        minTime = min(minTime, selected[i].start);
        maxTime = max(maxTime, selected[i].finish);
    }

    if (minTime == INT_MAX) minTime = 0;

    int totalTimeSpan = maxTime - minTime;
    int usedTime = 0;
    rep(i, 0, sz(selected)) {
        usedTime += (selected[i].finish - selected[i].start);
    }

    res.timeSlotCoverage = totalTimeSpan > 0 ? totalTimeSpan : 0;
    res.utilizationPercent = totalTimeSpan > 0 ? (100.0 * usedTime / totalTimeSpan) : 0;
    res.idleTimeMinutes = totalTimeSpan - usedTime;
    return res;
}

string renderHeader() {
    return R"HTML(
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Greedy Scheduling Studio</title>
  <style>
    :root {
      --bg: #0b1220;
      --panel: #121b2f;
      --panel-2: #17233c;
      --text: #e8eefc;
      --muted: #a9b7d0;
      --cyan: #4fd1c5;
      --green: #4ade80;
      --yellow: #facc15;
      --red: #fb7185;
      --blue: #60a5fa;
      --line: rgba(255,255,255,.08);
      --shadow: 0 18px 50px rgba(0,0,0,.35);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(79, 209, 197, .20), transparent 32%),
        radial-gradient(circle at top right, rgba(96, 165, 250, .18), transparent 24%),
        linear-gradient(180deg, #08111f 0%, #0b1220 100%);
      color: var(--text);
    }
    .wrap { max-width: 1280px; margin: 0 auto; padding: 32px 20px 48px; }
    .hero {
      padding: 40px 36px;
      background: linear-gradient(135deg, rgba(18,27,47,.98), rgba(23,35,60,.92));
      border: 1.5px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 20px 50px rgba(0,0,0,.4);
      margin-bottom: 28px;
      position: relative;
      overflow: hidden;
    }
    .hero::before {
      content: '';
      position: absolute;
      top: -1px;
      left: 0;
      right: 0;
      height: 1px;
      background: linear-gradient(to right, transparent, rgba(79, 209, 197, .3), transparent);
      pointer-events: none;
    }
    .title { 
      margin: 0;
      font-size: clamp(2.2rem, 5vw, 3.6rem);
      letter-spacing: -0.03em;
      font-weight: 900;
      background: linear-gradient(135deg, var(--cyan), var(--blue));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .subtitle { 
      color: var(--muted);
      margin: 14px 0 0;
      max-width: 900px;
      line-height: 1.7;
      font-size: 1.02rem;
    }
    .badges { 
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 22px;
    }
    .badge {
      padding: 8px 14px;
      border-radius: 10px;
      background: linear-gradient(135deg, rgba(79, 209, 197, .12), rgba(96, 165, 250, .08));
      border: 1.5px solid rgba(79, 209, 197, .2);
      color: var(--cyan);
      font-size: .9rem;
      font-weight: 600;
      backdrop-filter: blur(10px);
      letter-spacing: 0.01em;
    }
    .grid {
      display: grid;
      grid-template-columns: 1.1fr .9fr;
      gap: 18px;
      margin-top: 20px;
    }
    .card {
      background: linear-gradient(135deg, rgba(18,27,47,.95), rgba(12,18,35,.92));
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: var(--shadow);
      overflow: hidden;
      transition: all 0.3s ease;
    }
    .card:hover {
      border-color: rgba(79, 209, 197, .3);
      box-shadow: 0 24px 60px rgba(0,0,0,.4), 0 0 30px rgba(79, 209, 197, .15);
    }
    .card h2, .card h3 { margin: 0; }
    .card .head {
      padding: 20px 24px;
      color: var(--cyan);
      font-size: 1.2rem;
      font-weight: 800;
      background: linear-gradient(135deg, rgba(79, 209, 197, .1), rgba(96, 165, 250, .05));
      border-bottom: 1px solid var(--line);
      letter-spacing: -0.01em;
    }
    .card .body { padding: 24px; }
    textarea {
      width: 100%;
      min-height: 340px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: linear-gradient(135deg, #0a0f1d, #0d121f);
      color: var(--text);
      padding: 16px;
      font: inherit;
      line-height: 1.6;
      outline: none;
      transition: all 0.2s ease;
    }
    textarea:focus { 
      border-color: rgba(79, 209, 197, .8);
      box-shadow: 0 0 0 4px rgba(79, 209, 197, .15), inset 0 0 10px rgba(79, 209, 197, .05);
      background: linear-gradient(135deg, #0f1426, #121e32);
    }
    .hint { color: var(--muted); line-height: 1.7; margin: 12px 0 0; font-size: .95rem; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
    .btn {
      appearance: none;
      border: 0;
      padding: 13px 22px;
      border-radius: 12px;
      font: inherit;
      font-weight: 600;
      font-size: .95rem;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      letter-spacing: 0.01em;
    }
    .btn:active { transform: scale(0.98); }
    .btn-primary { 
      background: linear-gradient(135deg, var(--cyan), var(--blue));
      color: #07111e;
      box-shadow: 0 8px 24px rgba(79, 209, 197, .25);
    }
    .btn-primary:hover {
      box-shadow: 0 12px 32px rgba(79, 209, 197, .35);
      transform: translateY(-2px);
    }
    .btn-secondary { 
      background: rgba(255,255,255,.08);
      color: var(--text);
      border: 1.5px solid var(--line);
      backdrop-filter: blur(10px);
    }
    .btn-secondary:hover {
      background: rgba(255,255,255,.12);
      border-color: rgba(79, 209, 197, .5);
      transform: translateY(-1px);
    }
    .pill { 
      display: inline-block; 
      padding: 7px 14px; 
      border-radius: 8px;
      font-size: .87rem;
      margin-right: 8px;
      margin-bottom: 8px;
      font-weight: 500;
      backdrop-filter: blur(10px);
    }
    .pill-green { background: linear-gradient(135deg, rgba(74, 222, 128, .25), rgba(34, 197, 94, .15)); color: #86efac; border: 1px solid rgba(74, 222, 128, .3); }
    .pill-yellow { background: linear-gradient(135deg, rgba(250, 204, 21, .25), rgba(217, 119, 6, .15)); color: #fde047; border: 1px solid rgba(250, 204, 21, .3); }
    .pill-blue { background: linear-gradient(135deg, rgba(96, 165, 250, .25), rgba(59, 130, 246, .15)); color: #93c5fd; border: 1px solid rgba(96, 165, 250, .3); }
    .pill-red { background: linear-gradient(135deg, rgba(251, 113, 133, .25), rgba(239, 68, 68, .15)); color: #fca5a5; border: 1px solid rgba(251, 113, 133, .3); }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 16px;
      overflow: hidden;
      border-radius: 16px;
      box-shadow: inset 0 0 0 1px var(--line);
    }
    th, td { 
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      font-size: .95rem;
    }
    th { 
      color: var(--cyan);
      font-weight: 700;
      background: linear-gradient(135deg, rgba(79, 209, 197, .08), rgba(96, 165, 250, .05));
      letter-spacing: 0.01em;
    }
    tr:hover { background: rgba(79, 209, 197, .05); }
    tr:last-child td { border-bottom: none; }
    .section { 
      margin-top: 28px;
      padding-bottom: 4px;
    }
    .section h3 { 
      margin: 0 0 16px 0;
      font-size: 1.15rem;
      font-weight: 800;
      color: var(--cyan);
      letter-spacing: -0.01em;
    }
    .error-box, .ok-box, .info-box {
      padding: 16px 20px;
      border-radius: 14px;
      border: 1.5px solid var(--line);
      margin-top: 14px;
      font-size: .95rem;
      font-weight: 500;
      line-height: 1.6;
    }
    .error-box { 
      background: linear-gradient(135deg, rgba(251, 113, 133, .12), rgba(239, 68, 68, .08));
      color: #fecdd3;
      border-color: rgba(251, 113, 133, .25);
    }
    .ok-box { 
      background: linear-gradient(135deg, rgba(74, 222, 128, .12), rgba(34, 197, 94, .08));
      color: #bbf7d0;
      border-color: rgba(74, 222, 128, .25);
    }
    .info-box { 
      background: linear-gradient(135deg, rgba(96, 165, 250, .12), rgba(59, 130, 246, .08));
      color: #dbeafe;
      border-color: rgba(96, 165, 250, .25);
    }
    .timeline { display: grid; gap: 12px; margin-top: 12px; }
    .timeline-row { display: grid; grid-template-columns: 140px 1fr; gap: 14px; align-items: center; }
    .timeline-label { 
      color: var(--muted);
      font-size: .95rem;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 500;
    }
    .timeline-track {
      position: relative;
      height: 36px;
      border-radius: 12px;
      background: rgba(255,255,255,.04);
      border: 1.5px solid var(--line);
      overflow: hidden;
      box-shadow: inset 0 1px 3px rgba(0,0,0,.3);
    }
    .timeline-bar {
      position: absolute;
      top: 3px; bottom: 3px;
      border-radius: 10px;
      padding: 0 12px;
      display: flex;
      align-items: center;
      font-size: .87rem;
      color: #06111d;
      font-weight: 700;
      overflow: hidden;
      white-space: nowrap;
      box-shadow: 0 2px 8px rgba(0,0,0,.3);
      letter-spacing: 0.01em;
    }
    .timeline-bar-green { background: linear-gradient(135deg, #4ade80, #22c55e); }
    .timeline-bar-gold { background: linear-gradient(135deg, #facc15, #f59e0b); }
    .timeline-scale { 
      display: flex;
      justify-content: space-between;
      color: var(--muted);
      font-size: .82rem;
      margin-top: 12px;
      font-weight: 500;
    }
    .footer-note { 
      color: var(--muted);
      font-size: .92rem;
      margin-top: 18px;
      line-height: 1.7;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }
    @media (max-width: 960px) {
      .grid { grid-template-columns: 1fr; }
      .timeline-row { grid-template-columns: 1fr; }
    }
    input[type="checkbox"] {
      appearance: none;
      width: 18px;
      height: 18px;
      border: 2px solid var(--line);
      border-radius: 6px;
      background: rgba(79, 209, 197, .05);
      cursor: pointer;
      transition: all 0.25s ease;
      margin-right: 8px;
      flex-shrink: 0;
    }
    input[type="checkbox"]:hover {
      border-color: rgba(79, 209, 197, .4);
      background: rgba(79, 209, 197, .1);
    }
    input[type="checkbox"]:checked {
      background: linear-gradient(135deg, var(--cyan), var(--blue));
      border-color: var(--cyan);
      box-shadow: 0 0 10px rgba(79, 209, 197, .3);
    }
    input[type="checkbox"]:checked::after {
      content: '✓';
      display: flex;
      align-items: center;
      justify-content: center;
      color: #07111e;
      font-weight: 700;
      font-size: 12px;
    }
    select {
      padding: 10px 14px;
      border: 1.5px solid var(--line);
      border-radius: 10px;
      background: rgba(9, 17, 31, .8);
      color: var(--text);
      font: inherit;
      cursor: pointer;
      transition: all 0.25s ease;
      font-weight: 500;
    }
    select:hover {
      border-color: rgba(79, 209, 197, .4);
    }
    select:focus {
      outline: none;
      border-color: rgba(79, 209, 197, .8);
      box-shadow: 0 0 0 3px rgba(79, 209, 197, .1);
    }
  </style>
</head>
<body>
<div class="wrap">
)HTML";
}

string renderFooter() {
        return R"HTML(
</div>
<script>
document.addEventListener('DOMContentLoaded', function(){
    // Find all textareas on the page and set up auto-sizing
    const allTextareas = document.querySelectorAll('textarea[name="activities"]');
    allTextareas.forEach(function(ta){
        // auto-size each textarea
        function autosize(el){ if (!el) return; el.style.height = 'auto'; el.style.height = (el.scrollHeight) + 'px'; }
        autosize(ta);
        ta.addEventListener('input', function(){ autosize(this); });
    });

    // Add sample & copy buttons to action toolbars inside cards
    const actionContainers = document.querySelectorAll('.actions');
    actionContainers.forEach(function(ac){
        // Find the nearest ancestor card
        let node = ac;
        let card = null;
        while (node) {
            if (node.classList && node.classList.contains('card')) { card = node; break; }
            node = node.parentElement;
        }
        if (!card) return;
        
        // Find the textarea inside THIS card (scoped to this card)
        const cardTextarea = card.querySelector('textarea[name="activities"]');
        if (!cardTextarea) return;
        
        // Skip if buttons already added
        if (ac.querySelector('.btn-sample')) return;
        
        // Create Load Sample button
        const btnSample = document.createElement('button');
        btnSample.type = 'button';
        btnSample.className = 'btn btn-secondary btn-sample';
        btnSample.textContent = 'Load Sample';
        btnSample.addEventListener('click', async function(e){
            e.preventDefault();
            try {
                const res = await fetch('/sample-data');
                const text = await res.text();
                cardTextarea.value = text;
                cardTextarea.dispatchEvent(new Event('input'));
                cardTextarea.focus();
            } catch (err) {
                alert('Failed to load sample data: ' + err.message);
            }
        });
        
        // Create Copy button
        const btnCopy = document.createElement('button');
        btnCopy.type = 'button';
        btnCopy.className = 'btn btn-secondary';
        btnCopy.textContent = 'Copy';
        btnCopy.addEventListener('click', function(e){
            e.preventDefault();
            if (!cardTextarea || !cardTextarea.value) {
                alert('Nothing to copy.');
                return;
            }
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(cardTextarea.value).then(function(){
                    btnCopy.textContent = 'Copied!';
                    setTimeout(function(){ btnCopy.textContent = 'Copy'; }, 1500);
                }).catch(function(err){
                    alert('Copy failed: ' + err);
                });
            } else {
                cardTextarea.select();
                try {
                    document.execCommand('copy');
                    btnCopy.textContent = 'Copied!';
                    setTimeout(function(){ btnCopy.textContent = 'Copy'; }, 1500);
                } catch (err) {
                    alert('Copy failed: ' + err);
                }
            }
        });
        
        // Insert buttons at the start of the action container
        ac.insertBefore(btnSample, ac.firstChild);
        ac.insertBefore(btnCopy, ac.firstChild);
    });
    
    // Validate non-empty textarea on form submit
    const analyzeForms = document.querySelectorAll('form[method="POST"][action="/analyze"]');
    analyzeForms.forEach(function(form){
        const formTextarea = form.querySelector('textarea[name="activities"]');
        form.addEventListener('submit', function(e){
            if (!formTextarea || !formTextarea.value.trim()) {
                e.preventDefault();
                alert('Please enter at least one activity (one per line, format: Name,Start,Finish,Priority,Deadline).');
                if (formTextarea) formTextarea.focus();
                return false;
            }
        });
    });
});
</script>
</body>
</html>
)HTML";
}

string renderKeyValuePills(const vector<pair<string, string>>& items) {
    string out;
    for (const auto& item : items) {
        out += "<span class='pill pill-blue'>" + htmlEscape(item.first) + ": " + htmlEscape(item.second) + "</span>";
    }
    return out;
}

string renderActivitiesTable(const vector<Activity>& acts) {
    string out = "<table><thead><tr><th>ID</th><th>Activity</th><th>Start</th><th>Finish</th><th>Duration</th><th>Priority</th></tr></thead><tbody>";
    if (acts.empty()) {
        out += "<tr><td colspan='6'>No activities</td></tr>";
    } else {
        for (const auto& a : acts) {
            out += "<tr><td>" + to_string(a.id) + "</td><td>" + htmlEscape(activityNames[a.name_id]) + "</td><td>" +
                   htmlEscape(minutesToTime(a.start)) + "</td><td>" + htmlEscape(minutesToTime(a.finish)) + "</td><td>" +
                   to_string(a.finish - a.start) + " min</td><td>" + to_string(a.weight) + "</td></tr>";
        }
    }
    out += "</tbody></table>";
    return out;
}

string renderConflictsSection(const ConflictReport& report) {
    string out = "<div class='section'><h3>Conflict Analysis</h3>";
    if (!report.hasConflicts) {
        out += "<div class='ok-box'>No conflicts detected.</div>";
    } else {
        out += "<div class='error-box'>" + to_string(report.totalConflicts) + " conflict(s) found.</div>";
        out += "<table><thead><tr><th>Activity 1</th><th>Activity 2</th></tr></thead><tbody>";
        for (const auto& pairIds : report.conflictPairs) {
            out += "<tr><td>" + htmlEscape(activityNames[pairIds.first]) + "</td><td>" + htmlEscape(activityNames[pairIds.second]) + "</td></tr>";
        }
        out += "</tbody></table>";
    }
    out += "</div>";
    return out;
}

string renderAnalyticsBox(const AnalyticsResult& res) {
    string out;
    out += "<div class='info-box'>";
    out += "Total Activities: <b>" + to_string(res.totalActivities) + "</b><br>";
    out += "Selected Activities: <b>" + to_string(res.selectedActivities) + "</b><br>";
    out += "Total Weight/Priority: <b>" + to_string(res.totalWeight) + "</b><br>";
    out += "Time Slot Coverage: <b>" + to_string(res.timeSlotCoverage) + " minutes</b><br>";
    stringstream ss;
    ss << fixed << setprecision(1) << res.utilizationPercent;
    out += "Utilization Rate: <b>" + ss.str() + "%</b><br>";
    out += "Idle Time: <b>" + to_string(res.idleTimeMinutes) + " minutes</b>";
    out += "</div>";
    return out;
}

string renderTimelineSection(const vector<Activity>& acts, const string& title, const string& colorClass) {
    if (acts.empty()) return "";
    int minStart = INT_MAX, maxFinish = 0;
    for (const auto& a : acts) {
        minStart = min(minStart, a.start);
        maxFinish = max(maxFinish, a.finish);
    }
    minStart = (minStart / 30) * 30;
    int span = maxFinish - minStart;
    if (span <= 0) span = 30;

    vector<string> labels;
    for (int t = minStart; t <= maxFinish; t += 60) {
        labels.pb(minutesToTime(t));
    }

    string out = "<div class='section'><h3>" + htmlEscape(title) + "</h3><div class='timeline'>";
    for (const auto& a : acts) {
        double leftPct = 100.0 * (a.start - minStart) / span;
        double widthPct = 100.0 * (a.finish - a.start) / span;
        if (widthPct < 1.0) widthPct = 1.0;
        out += "<div class='timeline-row'><div class='timeline-label'>" + htmlEscape(activityNames[a.name_id]) + "</div>";
        out += "<div class='timeline-track'><div class='timeline-bar " + colorClass + "' style='left:" + to_string(leftPct) + "%; width:" + to_string(widthPct) + "%;'>";
        out += htmlEscape(minutesToTime(a.start) + " - " + minutesToTime(a.finish));
        out += "</div></div></div>";
    }
    out += "</div><div class='timeline-scale'>";
    for (const auto& label : labels) out += "<span>" + htmlEscape(label) + "</span>";
    out += "</div></div>";
    return out;
}

string renderRoomSection(const vector<vector<Activity>>& rooms, int roomCount) {
    string out = "<div class='section'><h3>Minimum Rooms Required</h3>";
    out += "<div class='ok-box'>Minimum rooms needed: <b>" + to_string(roomCount) + "</b></div>";
    if (!rooms.empty()) {
        out += "<table><thead><tr><th>Room</th><th>Activities</th></tr></thead><tbody>";
        for (size_t i = 0; i < rooms.size(); ++i) {
            string row;
            for (const auto& a : rooms[i]) {
                if (!row.empty()) row += "<br>";
                row += htmlEscape(activityNames[a.name_id] + " [" + minutesToTime(a.start) + " - " + minutesToTime(a.finish) + "]");
            }
            out += "<tr><td>Room " + to_string(i + 1) + "</td><td>" + row + "</td></tr>";
        }
        out += "</tbody></table>";
    }
    out += "</div>";
    return out;
}

string renderJobSummary(const vector<Activity>& allActs, const vector<Activity>& scheduled) {
    int totalProfit = 0;
    int maxDeadline = 0;
    for (const auto& a : allActs) maxDeadline = max(maxDeadline, a.deadline);
    for (const auto& a : scheduled) totalProfit += a.weight;
    string out = "<div class='section'><h3>Job Sequencing Summary</h3>";
    out += "<div class='info-box'>Scheduled Jobs: <b>" + to_string(sz(scheduled)) + "</b><br>";
    out += "Total Profit: <b>" + to_string(totalProfit) + "</b><br>";
    out += "Max Deadline Slot: <b>" + to_string(maxDeadline) + "</b><br>";
    out += "Note: This algorithm is deadline-based, not interval-based.</div></div>";
    return out;
}

string renderComparison(const AnalyticsResult& a1, const AnalyticsResult& a2, const vector<Activity>& jobSeq, const vector<Activity>& opt) {
    int jobProfit = 0;
    for (const auto& a : jobSeq) jobProfit += a.weight;
    AnalyticsResult optAnalytics{};
    if (!opt.empty()) {
        int minTime = INT_MAX, maxTime = 0, totalWeight = 0, usedTime = 0;
        for (const auto& a : opt) {
            totalWeight += a.weight;
            minTime = min(minTime, a.start);
            maxTime = max(maxTime, a.finish);
            usedTime += (a.finish - a.start);
        }
        if (minTime == INT_MAX) minTime = 0;
        int totalSpan = maxTime - minTime;
        optAnalytics.totalWeight = totalWeight;
        optAnalytics.selectedActivities = sz(opt);
        optAnalytics.utilizationPercent = totalSpan > 0 ? (100.0 * usedTime / totalSpan) : 0;
    }

    stringstream s1, s2, s3;
    s1 << fixed << setprecision(1) << a1.utilizationPercent;
    s2 << fixed << setprecision(1) << a2.utilizationPercent;
    s3 << fixed << setprecision(1) << optAnalytics.utilizationPercent;

    string out = "<div class='section'><h3>Comparison</h3><table><thead><tr><th>Algorithm</th><th>Selected</th><th>Weight / Profit</th><th>Utilization</th></tr></thead><tbody>";
    out += "<tr><td>Activity Selection</td><td>" + to_string(a1.selectedActivities) + "</td><td>" + to_string(a1.totalWeight) + "</td><td>" + s1.str() + "%</td></tr>";
    out += "<tr><td>Weighted Scheduling</td><td>" + to_string(a2.selectedActivities) + "</td><td>" + to_string(a2.totalWeight) + "</td><td>" + s2.str() + "%</td></tr>";
    out += "<tr><td>Job Sequencing (DSU)</td><td>" + to_string(sz(jobSeq)) + "</td><td>" + to_string(jobProfit) + "</td><td>-</td></tr>";
    out += "<tr><td>Weighted Interval DP</td><td>" + to_string(sz(opt)) + "</td><td>" + to_string(optAnalytics.totalWeight) + "</td><td>" + s3.str() + "%</td></tr>";
    out += "</tbody></table></div>";
    return out;
}

string renderHomePage(const string& prefill, const string& message = "") {
    string out = renderHeader();
    out += R"HTML(
<section class="hero">
  <h1 class="title">Greedy Scheduling Studio</h1>
  <p class="subtitle">A C++-only browser version of the timetable and scheduling project. Paste activities, analyze them with 5 algorithms, compare greedy vs optimal results, and download the optimal schedule as CSV.</p>
  <div class="badges">
    <span class="badge">Activity Selection</span>
    <span class="badge">Weighted Scheduling</span>
    <span class="badge">Job Sequencing</span>
    <span class="badge">Min Rooms</span>
    <span class="badge">DP Optimal</span>
  </div>
</section>
)HTML";
    if (!message.empty()) {
        out += message;
    }
    out += "<div class='grid'><div class='card'><div class='head'>Input Activities</div><div class='body'>";
    out += "<form id='analyze-form' method='POST' action='/analyze'>";
    out += "<textarea id='activities-textarea' name='activities' spellcheck='false'>" + htmlEscape(prefill) + "</textarea>";
    out += "<div class='hint'>One activity per line: <b>Name,Start,Finish,Priority,Deadline</b>. Example: <code>Math,09:00,10:00,5,12:00</code></div>";
    out += "<div class='section' style='margin-top:12px'><h3 style='margin:0 0 8px 0'>Algorithms</h3>";
    out += "<label style='display:inline-flex;align-items:center;margin-right:12px'><input type='checkbox' name='algo_actsel' checked> Activity Selection</label>";
    out += "<label style='display:inline-flex;align-items:center;margin-right:12px'><input type='checkbox' name='algo_weighted' checked> Weighted Greedy</label>";
    out += "<label style='display:inline-flex;align-items:center;margin-right:12px'><input type='checkbox' name='algo_jobseq' checked> Job Sequencing (DSU)</label>";
    out += "<label style='display:inline-flex;align-items:center;margin-right:12px'><input type='checkbox' name='algo_rooms' checked> Min Rooms</label>";
    out += "<label style='display:inline-flex;align-items:center;margin-right:12px'><input type='checkbox' name='algo_dp' checked> DP Optimal</label>";
    out += "</div>";
    out += "<div class='actions'><button class='btn btn-primary' type='submit'>Analyze Schedule</button><a class='btn btn-secondary' href='/'>Reset to Sample</a></div>";
    out += "</form></div></div>";
    out += "<div class='card'><div class='head'>How it works</div><div class='body'>";
    out += "<p class='hint'>This web app keeps the same core scheduling logic as the CLI version. The browser only replaces the menu and printout. The algorithms still compute the same selections, conflicts, room allocation, and DP-optimal schedule.</p>";
    out += renderKeyValuePills({
        {"Deadline input", "HH:MM"},
        {"Output", "Tables + timeline"},
        {"Server", "localhost:8080"},
        {"Language", "C++ only"}
    });
    out += "<div class='footer-note'>Tip: Use quotes around names that contain commas. One activity per line.</div>";
    out += "</div></div></div>";
    out += renderFooter();
    return out;
}

string renderResultsPage(const string& originalInput, const vector<Activity>& acts, const vector<string>& errors, const map<string,string>& form) {
    string message;
    if (!errors.empty()) {
        message = "<div class='error-box'><b>Input issues:</b><ul>";
        for (const auto& e : errors) message += "<li>" + htmlEscape(e) + "</li>";
        message += "</ul></div>";
    } else {
        message = "<div class='ok-box'>Analysis complete. Scroll for all algorithm results.</div>";
    }

    string out = renderHeader();
    out += R"HTML(
<section class="hero">
  <h1 class="title">Greedy Scheduling Studio</h1>
  <p class="subtitle">Browser analysis results for your activity set. The core scheduling logic is unchanged; the output is now rendered as a web dashboard.</p>
</section>
)HTML";
    out += message;

    out += "<div class='card'><div class='head'>Edit Input</div><div class='body'>";
    out += "<form id='analyze-form' method='POST' action='/analyze'>";
    out += "<textarea id='activities-textarea' name='activities' spellcheck='false'>" + htmlEscape(originalInput) + "</textarea>";
    // preserve algorithm checkbox states from form
    bool f_act = form.count("algo_actsel");
    bool f_w = form.count("algo_weighted");
    bool f_j = form.count("algo_jobseq");
    bool f_r = form.count("algo_rooms");
    bool f_d = form.count("algo_dp");
    out += "<div class='section' style='margin-top:12px'><h3 style='margin:0 0 8px 0'>Algorithms</h3>";
    out += string("<label style='display:inline-flex;align-items:center;margin-right:12px'><input type='checkbox' name='algo_actsel' ") + (f_act?"checked":"") + "> Activity Selection</label>";
    out += string("<label style='display:inline-flex;align-items:center;margin-right:12px'><input type='checkbox' name='algo_weighted' ") + (f_w?"checked":"") + "> Weighted Greedy</label>";
    out += string("<label style='display:inline-flex;align-items:center;margin-right:12px'><input type='checkbox' name='algo_jobseq' ") + (f_j?"checked":"") + "> Job Sequencing (DSU)</label>";
    out += string("<label style='display:inline-flex;align-items:center;margin-right:12px'><input type='checkbox' name='algo_rooms' ") + (f_r?"checked":"") + "> Min Rooms</label>";
    out += string("<label style='display:inline-flex;align-items:center;margin-right:12px'><input type='checkbox' name='algo_dp' ") + (f_d?"checked":"") + "> DP Optimal</label>";
    out += "</div>";
    out += "<div class='actions'><button class='btn btn-primary' type='submit'>Re-analyze</button><a class='btn btn-secondary' href='/'>Back Home</a></div>";
    out += "</form></div></div>";

    out += "<div class='section'><h3>Input Activities</h3>";
    out += renderActivitiesTable(acts);
    out += "</div>";

    ConflictReport conflicts = detectConflicts(acts);
    out += renderConflictsSection(conflicts);

    // Respect algorithm selections from the form
    bool doAct = form.count("algo_actsel");
    bool doWeighted = form.count("algo_weighted");
    bool doJobSeq = form.count("algo_jobseq");
    bool doRooms = form.count("algo_rooms");
    bool doDP = form.count("algo_dp");

    vector<Activity> sel1, sel2, sel3, sel5;
    vector<vector<Activity>> rooms;
    int roomCount = 0;
    AnalyticsResult a1{}; AnalyticsResult a2{}; AnalyticsResult a5{};

    if (doAct) {
        sel1 = activitySelection(acts);
        a1 = computeAnalytics(acts, sel1);
        out += "<div class='section'><h3>1. Activity Selection (Greedy)</h3>";
        out += renderActivitiesTable(sel1);
        out += renderAnalyticsBox(a1);
        out += renderTimelineSection(sel1, "Timeline", "timeline-bar-gold");
        out += "</div>";
    }

    if (doWeighted) {
        sel2 = weightedScheduling(acts);
        a2 = computeAnalytics(acts, sel2);
        out += "<div class='section'><h3>2. Priority-Based Weighted Scheduling (Greedy)</h3>";
        out += renderActivitiesTable(sel2);
        out += renderAnalyticsBox(a2);
        out += "</div>";
    }

    if (doJobSeq) {
        sel3 = jobSequencingDSU(acts);
        out += "<div class='section'><h3>3. Job Sequencing with Deadlines (DSU)</h3>";
        out += renderActivitiesTable(sel3);
        out += renderJobSummary(acts, sel3);
        out += "</div>";
    }

    if (doRooms) {
        roomCount = minRoomsRequired(acts, rooms);
        out += renderRoomSection(rooms, roomCount);
    }

    if (doDP) {
        sel5 = weightedIntervalSchedulingDP(acts);
        a5 = computeAnalytics(acts, sel5);
        out += "<div class='section'><h3>5. Weighted Interval Scheduling (DP - Optimal)</h3>";
        out += renderActivitiesTable(sel5);
        out += renderAnalyticsBox(a5);
        out += renderTimelineSection(sel5, "Optimal Timeline", "timeline-bar-green");
        out += "</div>";
    }

    out += renderComparison(a1, a2, sel3, sel5);

    out += "<div class='card'><div class='body'>";
    out += "<form method='POST' action='/download'>";
    out += "<textarea name='activities' style='display:none'>" + htmlEscape(originalInput) + "</textarea>";
    out += "<div style='margin:10px 0'><label style='margin-right:8px'>Download CSV for:</label>";
    out += "<select name='download_algo'>";
    out += "<option value='dp'>DP Optimal</option>";
    out += "<option value='act'>Activity Selection</option>";
    out += "<option value='weighted'>Weighted Greedy</option>";
    out += "<option value='jobseq'>Job Sequencing</option>";
    out += "<option value='rooms'>Rooms Allocation</option>";
    out += "</select></div>";
    out += "<div class='actions'><button class='btn btn-primary' type='submit'>Download CSV</button><a class='btn btn-secondary' href='/'>Start Over</a></div>";
    out += "</form></div></div>";

    out += renderFooter();
    return out;
}

string renderCsv(const vector<Activity>& acts) {
    ostringstream out;
    out << "ID,Activity,Start,Finish,Duration(min),Priority\n";
    for (const auto& a : acts) {
        out << a.id << "," << activityNames[a.name_id] << "," << minutesToTime(a.start) << "," << minutesToTime(a.finish) << "," << (a.finish - a.start) << "," << a.weight << "\n";
    }
    return out.str();
}

string sampleRequestMessage() {
    return "";
}

struct HttpRequest {
    string method;
    string path;
    map<string, string> headers;
    string body;
};

string statusLine(const string& status) {
    return "HTTP/1.1 " + status + "\r\n";
}

string buildResponse(const string& status, const string& contentType, const string& body, const string& extraHeaders = "") {
    ostringstream out;
    out << statusLine(status);
    out << "Content-Type: " << contentType << "\r\n";
    out << "Content-Length: " << body.size() << "\r\n";
    out << "Connection: close\r\n";
    if (!extraHeaders.empty()) out << extraHeaders;
    out << "\r\n";
    out << body;
    return out.str();
}

bool readHttpRequest(int client, HttpRequest& req) {
    string data;
    char buffer[4096];
    while (data.find("\r\n\r\n") == string::npos) {
        ssize_t received = recv(client, buffer, sizeof(buffer), 0);
        if (received <= 0) return false;
        data.append(buffer, buffer + received);
        if (data.size() > 1024 * 1024) return false;
    }

    size_t headerEnd = data.find("\r\n\r\n");
    string headerPart = data.substr(0, headerEnd);
    req.body = data.substr(headerEnd + 4);

    istringstream headerStream(headerPart);
    string requestLine;
    getline(headerStream, requestLine);
    requestLine = trim(requestLine);
    istringstream lineStream(requestLine);
    lineStream >> req.method >> req.path;

    string headerLine;
    while (getline(headerStream, headerLine)) {
        headerLine = trim(headerLine);
        if (headerLine.empty()) continue;
        size_t colon = headerLine.find(':');
        if (colon != string::npos) {
            string key = trim(headerLine.substr(0, colon));
            string value = trim(headerLine.substr(colon + 1));
            req.headers[key] = value;
        }
    }

    size_t contentLength = 0;
    auto it = req.headers.find("Content-Length");
    if (it != req.headers.end()) contentLength = static_cast<size_t>(stoul(it->second));

    // Limit maximum POST body size to 1MB to avoid resource abuse
    const size_t MAX_BODY = 1 << 20; // 1 MiB
    if (contentLength > MAX_BODY) return false;

    while (req.body.size() < contentLength) {
        ssize_t received = recv(client, buffer, sizeof(buffer), 0);
        if (received <= 0) break;
        req.body.append(buffer, buffer + received);
        if (req.body.size() > MAX_BODY) return false;
    }

    return true;
}

string handleHome() {
    return renderHomePage(sampleActivitiesText());
}

string handleAnalyze(const string& body) {
    auto form = parseFormUrlEncoded(body);
    string input = form.count("activities") ? form["activities"] : sampleActivitiesText();
    vector<string> errors;
    vector<Activity> acts = parseActivitiesFromText(input, errors);
    if (acts.empty() && errors.empty()) {
        errors.pb("No valid activities were provided.");
    }
    return renderResultsPage(input, acts, errors, form);
}

string handleDownload(const string& body) {
    auto form = parseFormUrlEncoded(body);
    string input = form.count("activities") ? form["activities"] : sampleActivitiesText();
    vector<string> errors;
    vector<Activity> acts = parseActivitiesFromText(input, errors);
    string which = form.count("download_algo") ? form["download_algo"] : string("dp");
    string csv;
    string filename = "schedule_output.csv";

    if (which == "act") {
        auto sel = activitySelection(acts);
        csv = renderCsv(sel);
        filename = "activity_selection.csv";
    } else if (which == "weighted") {
        auto sel = weightedScheduling(acts);
        csv = renderCsv(sel);
        filename = "weighted_greedy.csv";
    } else if (which == "jobseq") {
        auto sel = jobSequencingDSU(acts);
        csv = renderCsv(sel);
        filename = "job_sequencing.csv";
    } else if (which == "rooms") {
        vector<vector<Activity>> rooms;
        minRoomsRequired(acts, rooms);
        // CSV header: Room,ID,Activity,Start,Finish,Duration,Priority
        ostringstream out;
        out << "Room,ID,Activity,Start,Finish,Duration(min),Priority\n";
        for (size_t r = 0; r < rooms.size(); ++r) {
            for (const auto& a : rooms[r]) {
                out << (r+1) << "," << a.id << "," << activityNames[a.name_id] << "," << minutesToTime(a.start) << "," << minutesToTime(a.finish) << "," << (a.finish - a.start) << "," << a.weight << "\n";
            }
        }
        csv = out.str();
        filename = "rooms_allocation.csv";
    } else {
        auto optimal = weightedIntervalSchedulingDP(acts);
        csv = renderCsv(optimal);
        filename = "optimal_schedule.csv";
    }

    return buildResponse("200 OK", "text/csv; charset=utf-8", csv,
                         string("Content-Disposition: attachment; filename=\"") + filename + "\"\r\n");
}

string handleRequest(const HttpRequest& req) {
    if (req.method == "GET" && (req.path == "/" || req.path == "/index.html")) {
        return buildResponse("200 OK", "text/html; charset=utf-8", handleHome());
    }
    if (req.method == "POST" && req.path == "/analyze") {
        return buildResponse("200 OK", "text/html; charset=utf-8", handleAnalyze(req.body));
    }
    if (req.method == "POST" && req.path == "/download") {
        return handleDownload(req.body);
    }
    if (req.method == "GET" && req.path == "/sample-data") {
        return buildResponse("200 OK", "text/plain; charset=utf-8", sampleActivitiesText());
    }
    const string notFound = "<h1>404 Not Found</h1><p>The requested route was not found.</p>";
    return buildResponse("404 Not Found", "text/html; charset=utf-8", notFound);
}

void sendAll(int client, const string& response) {
    size_t sent = 0;
    while (sent < response.size()) {
        ssize_t n = send(client, response.data() + sent, response.size() - sent, 0);
        if (n <= 0) break;
        sent += static_cast<size_t>(n);
    }
}

int main() {
    fastio;

    int serverFd = socket(AF_INET, SOCK_STREAM, 0);
    if (serverFd < 0) {
        cerr << "Failed to create socket\n";
        return 1;
    }

    int opt = 1;
    setsockopt(serverFd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(8080);

    if (::bind(serverFd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) < 0) {
        cerr << "Failed to bind to port 8080\n";
        close(serverFd);
        return 1;
    }

    if (listen(serverFd, 8) < 0) {
        cerr << "Failed to listen\n";
        close(serverFd);
        return 1;
    }

    cout << "Greedy Scheduling Studio web app running at http://localhost:8080\n";
    cout << "Open that URL in your browser. Press Ctrl+C to stop.\n";

    while (true) {
        sockaddr_in clientAddr{};
        socklen_t clientLen = sizeof(clientAddr);
        int clientFd = accept(serverFd, reinterpret_cast<sockaddr*>(&clientAddr), &clientLen);
        if (clientFd < 0) continue;

        // handle each connection on a detached thread for basic concurrency
        std::thread([clientFd]() {
            HttpRequest req;
            if (readHttpRequest(clientFd, req)) {
                string response = handleRequest(req);
                sendAll(clientFd, response);
            }
            close(clientFd);
        }).detach();
    }

    close(serverFd);
    return 0;
}
